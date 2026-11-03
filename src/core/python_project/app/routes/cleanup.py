from uuid import UUID

from celery.schedules import crontab
from fastapi import Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from redbeat import RedBeatSchedulerEntry

from app import audit, auth, cleanup, machines, notifier
from app.initialized import celery_app, fastapi_app

SCHEDULE_TASK = "Cleanup_Storage"


# Tasks

def finish_message(storage_name: str, status: str, summary: dict) -> str:
    if status == "success":
        return f"[{storage_name}] Cleaning finished. {cleanup.summary_text(summary)}"
    # A failed cleaning alerts the channel, as a failed backup or restore does.
    return f"<!channel> [{storage_name}] Cleaning FAILED. {cleanup.summary_text(summary)} See the log in BackROLL."


@celery_app.task(name=SCHEDULE_TASK)
def cleanup_storage(storage_id, trigger="scheduled", user=None, run_id=None):
    """Deletes the old backups of every repository of a storage."""
    storage = cleanup.get_storage(UUID(storage_id))
    if storage is None:
        return {"skipped": "storage not found"}
    settings = cleanup.get_settings(storage.id)
    keep_days = settings.keep_days if settings else cleanup.DEFAULT_KEEP_DAYS
    hook_id = settings.hook_id if settings else None

    if run_id is None:
        if cleanup.has_running_run(storage.id):
            return {"skipped": "a cleaning of this storage is already running"}
        run_id = cleanup.create_run(storage, "prune", trigger, user)
    else:
        run_id = UUID(run_id)

    log = cleanup.Log()
    cleanup.notify(hook_id, f"[{storage.name}] Cleaning of the old backups started.",
                   notifier.cleaning_started_blocks(storage.name, "old"))
    try:
        summary = cleanup.prune_storage(storage.path, keep_days, log)
    except Exception as exception:
        log.add(f"ERROR {exception}")
        summary = {"repositories": 0, "archives_deleted": 0, "freed_bytes": 0, "errors": 1}
    status = "failed" if summary["errors"] else "success"
    log.add(cleanup.summary_text(summary))
    cleanup.finish_run(run_id, status, summary, log)
    cleanup.notify(hook_id, finish_message(storage.name, status, summary),
                   notifier.cleaning_finished_blocks(storage.name, "old", status, summary))
    return summary


@celery_app.task(name="Simulate_Cleanup")
def simulate_cleanup(storage_id):
    """What the cleaning of a storage would delete with the saved number of days. Deletes nothing."""
    storage = cleanup.get_storage(UUID(storage_id))
    if storage is None:
        raise ValueError("Storage not found.")
    settings = cleanup.get_settings(storage.id)
    keep_days = settings.keep_days if settings else cleanup.DEFAULT_KEEP_DAYS
    return {"storage_id": storage_id, "keep_days": keep_days, **cleanup.plan_storage(storage.path, keep_days)}


@celery_app.task(name="Delete_Selected_Backups")
def delete_selected_backups(storage_id, selection, run_id):
    """Deletes the backups chosen after a simulation, the ones that the rule still says to delete."""
    log = cleanup.Log()
    summary = {"repositories": 0, "archives_deleted": 0, "freed_bytes": 0, "errors": 0}
    storage = cleanup.get_storage(UUID(storage_id))
    settings = cleanup.get_settings(UUID(storage_id)) if storage else None
    hook_id = settings.hook_id if settings else None
    storage_name = storage.name if storage else storage_id
    try:
        if storage is None:
            raise ValueError("The storage does not exist any more.")
        keep_days = settings.keep_days if settings else cleanup.DEFAULT_KEEP_DAYS
        cleanup.notify(hook_id, f"[{storage_name}] Cleaning of the old backups started.",
                       notifier.cleaning_started_blocks(storage_name, "old"))
        log.add(f"Deletion of the backups chosen after a simulation ({keep_days} days).")
        summary = cleanup.delete_selected(storage.path, selection, keep_days, log)
    except Exception as exception:
        log.add(f"ERROR {exception}")
        summary["errors"] += 1
    finally:
        # Always: a run that stays "running" would block the next cleanings of the storage.
        status = "failed" if summary["errors"] else "success"
        log.add(cleanup.summary_text(summary))
        cleanup.finish_run(UUID(run_id), status, summary, log)
    cleanup.notify(hook_id, finish_message(storage_name, status, summary),
                   notifier.cleaning_finished_blocks(storage_name, "old", status, summary))
    return summary


def start_or_fail(run_id, task, args):
    """Starts a task. When the broker does not answer, the run is ended: a run left "running" blocks the storage."""
    try:
        task.apply_async(args=args)
    except Exception as exception:
        log = cleanup.Log()
        log.add(f"ERROR the cleaning could not be started: {exception}")
        cleanup.finish_run(run_id, "failed", {"repositories": 0, "archives_deleted": 0, "freed_bytes": 0, "errors": 1}, log)
        raise HTTPException(503, "The cleaning could not be started.")


def machine_names():
    """The names of the machines that exist, and why that list may be incomplete: see machines.py."""
    return machines.list_machine_names()


@celery_app.task(name="Scan_Orphan_Backups")
def scan_orphan_backups(storage_id):
    """The repositories of a storage whose machine no longer exists. Deletes nothing."""
    storage = cleanup.get_storage(UUID(storage_id))
    if storage is None:
        raise ValueError("Storage not found.")
    names, warnings = machine_names()
    complete = not warnings
    orphans = cleanup.find_orphans(storage.path, names) if complete else []
    return {"storage_id": storage_id, "complete": complete, "warnings": warnings,
            "machines": len(names), "orphans": orphans}


@celery_app.task(name="Delete_Orphan_Backups")
def delete_orphan_backups(storage_id, repositories, run_id):
    """Deletes the chosen repositories, after listing the machines again at this moment."""
    log = cleanup.Log()
    summary = {"repositories": 0, "archives_deleted": 0, "freed_bytes": 0, "errors": 0}
    storage = cleanup.get_storage(UUID(storage_id))
    settings = cleanup.get_settings(UUID(storage_id)) if storage else None
    hook_id = settings.hook_id if settings else None
    storage_name = storage.name if storage else storage_id
    try:
        if storage is None:
            raise ValueError("The storage does not exist any more.")
        cleanup.notify(hook_id, f"[{storage_name}] Deletion of the backups of deleted machines started.",
                       notifier.cleaning_started_blocks(storage_name, "deleted"))
        names, warnings = machine_names()
        if warnings:
            for warning in warnings:
                log.add(f"REFUSED: {warning}")
            summary["errors"] += 1
        else:
            for name in repositories:
                if name in names:
                    log.add(f"{name}: skipped, this machine exists.")
                    continue
                result = cleanup.delete_repository(storage.path, name, log)
                if result["deleted"]:
                    summary["repositories"] += 1
                    summary["archives_deleted"] += result["archives"]
                    summary["freed_bytes"] += result["size_bytes"]
    except Exception as exception:
        log.add(f"ERROR {exception}")
        summary["errors"] += 1
    finally:
        # Always: a run that stays "running" would block the next cleanings of the storage.
        status = "failed" if summary["errors"] else "success"
        log.add(cleanup.summary_text(summary))
        cleanup.finish_run(UUID(run_id), status, summary, log)
    cleanup.notify(hook_id, finish_message(storage_name, status, summary),
                   notifier.cleaning_finished_blocks(storage_name, "deleted", status, summary))
    return summary


# Schedule

def schedule_name(storage_id) -> str:
    return f"{SCHEDULE_TASK}-{storage_id}"


def sync_schedule(storage_id: UUID):
    """The schedule of the cleaning of a storage, in the scheduler of the application."""
    name = schedule_name(storage_id)
    try:
        RedBeatSchedulerEntry.from_key(f"redbeat:{name}", app=celery_app).delete()
    except Exception:
        # No entry yet, or the scheduler was emptied.
        pass
    settings = cleanup.get_settings(storage_id)
    if settings and settings.scheduled:
        minute, hour, day, month, weekday = settings.schedule.split()
        cron = crontab(minute=minute, hour=hour, day_of_month=day, month_of_year=month,
                       day_of_week=cleanup.celery_day_of_week(weekday))
        RedBeatSchedulerEntry(name, SCHEDULE_TASK, cron, args=(str(storage_id), "scheduled", None),
                              app=celery_app).save()


def forget_storage(storage_id: UUID):
    """The storage is being deleted: its settings reference it, and its schedule would run for nothing."""
    cleanup.delete_settings(storage_id)
    sync_schedule(storage_id)


def sync_all_schedules():
    for item in cleanup.list_settings():
        try:
            sync_schedule(UUID(item["storage_id"]))
        except Exception as exception:
            print(f"Unable to schedule the cleaning of {item['storage_name']}. {exception}")


# Routes

class SettingsUpdate(BaseModel):
    keep_days: int = Field(ge=1, le=100000)
    after_backup: bool = False
    scheduled: bool = False
    schedule: str = Field(default=cleanup.DEFAULT_SCHEDULE, max_length=64)
    hook_id: UUID | None = None


class StorageRequest(BaseModel):
    storage_id: UUID


class DeleteRequest(BaseModel):
    storage_id: UUID
    repositories: list[str] = Field(min_length=1, max_length=500)


class SelectionRequest(BaseModel):
    storage_id: UUID
    # {repository: [archive names]}
    backups: dict[str, list[str]] = Field(min_length=1, max_length=500)


def get_storage_or_404(storage_id: UUID):
    storage = cleanup.get_storage(storage_id)
    if storage is None:
        raise HTTPException(404, "Storage not found.")
    return storage


@fastapi_app.get("/api/v1/cleanup/settings", status_code=200)
def get_cleanup_settings(identity: dict = Depends(auth.require_viewer)):
    return {"storages": cleanup.list_settings()}


@fastapi_app.put("/api/v1/cleanup/settings/{storage_id}", status_code=200)
def put_cleanup_settings(storage_id: UUID, item: SettingsUpdate, request: Request,
                         identity: dict = Depends(auth.require_admin)):
    try:
        saved = cleanup.save_settings(storage_id, item.keep_days, item.after_backup, item.scheduled,
                                      item.schedule, item.hook_id)
    except LookupError as exception:
        raise HTTPException(404, str(exception))
    except ValueError as exception:
        raise HTTPException(422, str(exception))
    try:
        sync_schedule(storage_id)
    except Exception as exception:
        raise HTTPException(500, f"The settings are saved but the schedule could not be set. {exception}")
    audit.set_detail(request, f"{saved['storage_name']}: keep_days={item.keep_days}, "
                              f"after_backup={item.after_backup}, scheduled={item.scheduled} {item.schedule}")
    return saved


@fastapi_app.post("/api/v1/cleanup/run", status_code=202)
def run_cleanup(item: StorageRequest, request: Request, identity: dict = Depends(auth.require_admin)):
    storage = get_storage_or_404(item.storage_id)
    if cleanup.has_running_run(storage.id):
        raise HTTPException(409, "A cleaning of this storage is already running.")
    run_id = cleanup.create_run(storage, "prune", "manual", identity["username"])
    start_or_fail(run_id, cleanup_storage, (str(storage.id), "manual", identity["username"], str(run_id)))
    audit.set_detail(request, storage.name)
    return {"run_id": str(run_id)}


@fastapi_app.post("/api/v1/cleanup/simulate", status_code=202)
def simulate(item: StorageRequest, identity: dict = Depends(auth.require_admin)):
    get_storage_or_404(item.storage_id)
    task = simulate_cleanup.apply_async(args=(str(item.storage_id),))
    return {"Location": fastapi_app.url_path_for("retrieve_task_status", task_id=task.id)}


@fastapi_app.post("/api/v1/cleanup/selection/delete", status_code=202)
def delete_selection(item: SelectionRequest, request: Request, identity: dict = Depends(auth.require_admin)):
    storage = get_storage_or_404(item.storage_id)
    count = 0
    for name, archives in item.backups.items():
        if not cleanup.REPOSITORY_NAME.match(name) or name in cleanup.IGNORED or name.startswith("."):
            raise HTTPException(422, f"“{name}” is not a valid repository name.")
        if not archives or len(archives) > 5000 or not all(cleanup.valid_archive_name(a) for a in archives):
            raise HTTPException(422, f"The backups chosen for “{name}” are not valid.")
        count += len(archives)
    if cleanup.has_running_run(storage.id):
        raise HTTPException(409, "A cleaning of this storage is already running.")
    run_id = cleanup.create_run(storage, "prune", "manual", identity["username"])
    start_or_fail(run_id, delete_selected_backups, (str(storage.id), item.backups, str(run_id)))
    audit.set_detail(request, f"{storage.name}: {count} chosen backup(s) in {len(item.backups)} repository(ies)")
    return {"run_id": str(run_id)}


@fastapi_app.post("/api/v1/cleanup/orphans/scan", status_code=202)
def scan_orphans(item: StorageRequest, identity: dict = Depends(auth.require_admin)):
    get_storage_or_404(item.storage_id)
    task = scan_orphan_backups.apply_async(args=(str(item.storage_id),))
    return {"Location": fastapi_app.url_path_for("retrieve_task_status", task_id=task.id)}


@fastapi_app.post("/api/v1/cleanup/orphans/delete", status_code=202)
def delete_orphans(item: DeleteRequest, request: Request, identity: dict = Depends(auth.require_admin)):
    storage = get_storage_or_404(item.storage_id)
    for name in item.repositories:
        if not cleanup.REPOSITORY_NAME.match(name) or name in cleanup.IGNORED or name.startswith("."):
            raise HTTPException(422, f"“{name}” is not a valid repository name.")
    if cleanup.has_running_run(storage.id):
        raise HTTPException(409, "A cleaning of this storage is already running.")
    run_id = cleanup.create_run(storage, "orphans", "manual", identity["username"])
    start_or_fail(run_id, delete_orphan_backups, (str(storage.id), item.repositories, str(run_id)))
    audit.set_detail(request, f"{storage.name}: {', '.join(item.repositories)}"[:900])
    return {"run_id": str(run_id)}


@fastapi_app.get("/api/v1/cleanup/runs", status_code=200)
def list_cleanup_runs(limit: int = Query(50, ge=1, le=200), storage_id: UUID | None = None,
                      identity: dict = Depends(auth.require_viewer)):
    return {"items": cleanup.list_runs(limit, storage_id)}


@fastapi_app.get("/api/v1/cleanup/runs/{run_id}", status_code=200)
def get_cleanup_run(run_id: UUID, identity: dict = Depends(auth.require_viewer)):
    run = cleanup.get_run(run_id)
    if run is None:
        raise HTTPException(404, "Run not found.")
    return run
