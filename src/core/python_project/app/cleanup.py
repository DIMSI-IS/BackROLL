"""Cleaning of the backup storages: old backups, and the backups of machines that no longer exist.

It replaces the shell scripts that ran `borg prune --keep-daily=N` on every repository of a storage,
and removed by hand the repositories of deleted machines. Every cleaning is recorded with its log
and a summary, and can tell an external hook (Slack) when it starts and ends.
"""

import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from sqlmodel import Session, col, select, update

from app import archives as archive_names, protection
from app.auth.password import get_engine
from app import notifier
from app.database import CleanupRun, ExternalHooks, Storage, StorageCleanup

LOCK_WAIT_SECONDS = 5
MAX_LOG = 200_000
INTERRUPTED_HOURS = 12
REPOSITORY_NAME = re.compile(r"^[A-Za-z0-9._-]+$")
IGNORED = protection.IGNORED_FOLDERS
DEFAULT_KEEP_DAYS = 30
DEFAULT_SCHEDULE = "0 4 * * 0"
MIN_DAYS, MAX_DAYS = 1, 3650


def now() -> datetime:
    return datetime.now(timezone.utc)


class Log:
    """The log of a cleaning: it is shown in the interface, and stored with the run."""

    def __init__(self):
        self.lines: list[str] = []

    def add(self, text: str):
        stamp = now().strftime("%Y-%m-%d %H:%M:%S")
        for line in str(text).splitlines() or [""]:
            self.lines.append(f"{stamp} {line}")

    def text(self) -> str:
        text = "\n".join(self.lines)
        return text[-MAX_LOG:]


def run_borg(arguments: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(["borg", *arguments], capture_output=True, text=True)


def repository_size(repository: Path) -> int | None:
    """What the repository takes on the disk, deduplicated and compressed."""
    result = run_borg(["info", "--json", "--lock-wait", str(LOCK_WAIT_SECONDS), str(repository)])
    if result.returncode != 0:
        return None
    try:
        return int(json.loads(result.stdout)["cache"]["stats"]["unique_csize"])
    except (ValueError, KeyError):
        return None


def list_archives(repository: Path) -> list[dict]:
    result = run_borg(["list", "--json", "--lock-wait", str(LOCK_WAIT_SECONDS), str(repository)])
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "borg list failed")
    return json.loads(result.stdout).get("archives", [])


def archive_prefixes(archives: list[dict]) -> list[str]:
    """The groups of archives of a repository: one per disk, one per folder of the policy.
    The retention is applied to each of them apart, never to a wider set."""
    return archive_names.groups(archives)


def prune_repository(repository: Path, keep_days: int, log: Log) -> dict:
    """Keeps one archive per day for `keep_days` days, for each kind of archive. Then frees the space."""
    result = {"archives_deleted": 0, "freed_bytes": 0, "errors": 0}
    if not (repository / "config").is_file():
        log.add(f"{repository.name}: not a Borg repository, skipped.")
        return result
    if is_in_use(repository):
        # A backup is writing in it: this is not a failure, the next cleaning takes care of it.
        log.add(f"{repository.name}: skipped, the repository is in use.")
        return result
    try:
        archives = list_archives(repository)
    except Exception as exception:
        log.add(f"{repository.name}: ERROR {exception}")
        result["errors"] += 1
        return result

    before = repository_size(repository)
    for prefix in archive_prefixes(archives):
        pruned = run_borg(["prune", "-v", "--list", "--lock-wait", str(LOCK_WAIT_SECONDS),
                           "--keep-daily", str(keep_days), "--glob-archives", archive_names.glob_of(prefix), str(repository)])
        output = (pruned.stdout + pruned.stderr).strip()
        if pruned.returncode not in (0, 1):
            log.add(f"{repository.name}: ERROR while cleaning “{prefix}”: {output}")
            result["errors"] += 1
            continue
        deleted = [line for line in output.splitlines() if line.startswith("Pruning archive")]
        result["archives_deleted"] += len(deleted)
        for line in deleted:
            log.add(f"{repository.name}: {line.strip()}")
        if not deleted:
            log.add(f"{repository.name}: nothing to delete for “{prefix}”.")

    if result["archives_deleted"]:
        # Since Borg 1.2 the space is freed by a separate step.
        compacted = run_borg(["compact", "--lock-wait", str(LOCK_WAIT_SECONDS), str(repository)])
        if compacted.returncode not in (0, 1):
            log.add(f"{repository.name}: the space could not be freed. {compacted.stderr.strip()}")
            result["errors"] += 1
        after = repository_size(repository)
        if before is not None and after is not None and before > after:
            result["freed_bytes"] = before - after
    return result


def list_repositories(storage_path: str) -> list[Path]:
    return protection.find_repositories(storage_path)


WOULD_PRUNE = "Would prune:"
DELETE_BATCH = 50
MAX_ARCHIVE_NAME = 255


def plan_repository(repository: Path, keep_days: int) -> dict:
    """What a cleaning would delete in a repository, said by Borg itself (`prune --dry-run`): nothing is deleted."""
    archives = list_archives(repository)
    known = sorted((archive["name"] for archive in archives), key=len, reverse=True)
    details = {archive["name"]: archive for archive in archives}
    doomed: dict[str, dict] = {}
    for prefix in archive_prefixes(archives):
        pruned = run_borg(["prune", "--dry-run", "-v", "--list", "--lock-wait", str(LOCK_WAIT_SECONDS),
                           "--keep-daily", str(keep_days), "--glob-archives", archive_names.glob_of(prefix),
                           str(repository)])
        if pruned.returncode not in (0, 1):
            raise RuntimeError((pruned.stdout + pruned.stderr).strip() or "borg prune failed")
        for line in (pruned.stdout + pruned.stderr).splitlines():
            if WOULD_PRUNE not in line:
                continue
            rest = line.split(WOULD_PRUNE, 1)[1].strip()
            name = next((candidate for candidate in known if rest == candidate or rest.startswith(candidate + " ")), None)
            if name:
                doomed[name] = {"name": name, "group": archive_names.group_of(name),
                                "time": details[name].get("time") or details[name].get("start")}
    delete = sorted(doomed.values(), key=lambda item: (item["time"] or "", item["name"]))
    return {"name": repository.name, "total": len(archives), "delete": delete, "kept": len(archives) - len(delete)}


def plan_storage(storage_path: str, keep_days: int) -> dict:
    """The simulation of a cleaning of a whole storage. Only the repositories with something to delete are listed."""
    repositories, errors, total = [], [], 0
    for repository in list_repositories(storage_path):
        try:
            plan = plan_repository(repository, keep_days)
        except Exception as exception:
            errors.append({"name": repository.name, "error": str(exception)[:300]})
            continue
        total += len(plan["delete"])
        if plan["delete"]:
            repositories.append(plan)
    return {"repositories": repositories, "archives": total, "errors": errors}


def valid_archive_name(name) -> bool:
    return isinstance(name, str) and 0 < len(name) <= MAX_ARCHIVE_NAME and not name.startswith("-") \
        and "\n" not in name and "\r" not in name and "::" not in name


def delete_selected(storage_path: str, selection: dict[str, list[str]], keep_days: int, log: Log) -> dict:
    """Deletes the backups chosen after a simulation. What Borg says now must still agree: a backup that the rule
    keeps (a newer backup came, the number of days changed) is never deleted, whatever was asked."""
    summary = {"repositories": 0, "archives_deleted": 0, "freed_bytes": 0, "errors": 0}
    root = Path(storage_path).resolve()
    for name, chosen in selection.items():
        if not REPOSITORY_NAME.match(name) or name in IGNORED or name.startswith("."):
            log.add(f"{name}: refused, not a valid repository name.")
            continue
        repository = root / name
        if repository.is_symlink() or repository.resolve().parent != root or not (repository / "config").is_file():
            log.add(f"{name}: refused, not a Borg repository of this storage.")
            continue
        if is_in_use(repository):
            log.add(f"{name}: skipped, the repository is in use.")
            continue
        try:
            allowed = {item["name"] for item in plan_repository(repository, keep_days)["delete"]}
        except Exception as exception:
            log.add(f"{name}: ERROR {exception}")
            summary["errors"] += 1
            continue
        todo = [item for item in dict.fromkeys(chosen) if valid_archive_name(item) and item in allowed]
        for item in chosen:
            if item not in todo:
                log.add(f"{name}: {item} skipped, it is not to be deleted any more.")
        if not todo:
            continue
        before = repository_size(repository)
        deleted = 0
        for start in range(0, len(todo), DELETE_BATCH):
            batch = todo[start:start + DELETE_BATCH]
            result = run_borg(["delete", "--lock-wait", str(LOCK_WAIT_SECONDS), str(repository), *batch])
            if result.returncode not in (0, 1):
                log.add(f"{name}: ERROR while deleting backups: {(result.stdout + result.stderr).strip()}")
                summary["errors"] += 1
                break
            deleted += len(batch)
            for item in batch:
                log.add(f"{name}: backup {item} deleted.")
        if deleted:
            compacted = run_borg(["compact", "--lock-wait", str(LOCK_WAIT_SECONDS), str(repository)])
            if compacted.returncode not in (0, 1):
                log.add(f"{name}: the space could not be freed. {compacted.stderr.strip()}")
                summary["errors"] += 1
            after = repository_size(repository)
            if before is not None and after is not None and before > after:
                summary["freed_bytes"] += before - after
            summary["repositories"] += 1
            summary["archives_deleted"] += deleted
    return summary


def prune_storage(storage_path: str, keep_days: int, log: Log) -> dict:
    summary = {"repositories": 0, "archives_deleted": 0, "freed_bytes": 0, "errors": 0}
    repositories = list_repositories(storage_path)
    log.add(f"{len(repositories)} repository(ies) in {storage_path}. "
            f"One backup per day is kept for {keep_days} days.")
    for repository in repositories:
        result = prune_repository(repository, keep_days, log)
        summary["repositories"] += 1
        for key in ("archives_deleted", "freed_bytes", "errors"):
            summary[key] += result[key]
    return summary


def directory_size(path: Path) -> int:
    total = 0
    for root, _, files in os.walk(path):
        for name in files:
            try:
                total += os.path.getsize(os.path.join(root, name))
            except OSError:
                pass
    return total


def describe_repository(repository: Path) -> dict:
    """What the administrator needs to decide about a repository of a deleted machine."""
    last_backup, archives = None, 0
    try:
        found = list_archives(repository)
        archives = len(found)
        last_backup = protection.summarize(found)["last_backup"]
    except Exception:
        pass
    return {"name": repository.name, "last_backup": last_backup, "archives": archives,
            "size_bytes": directory_size(repository)}


def find_orphans(storage_path: str, machine_names: set[str]) -> list[dict]:
    """The repositories whose machine is not in the list. The caller makes sure the list is complete."""
    return [describe_repository(repository) for repository in list_repositories(storage_path)
            if repository.name not in machine_names]


def is_in_use(repository: Path) -> bool:
    return any((repository / name).exists() for name in ("lock.exclusive", "lock.roster"))


def delete_repository(storage_path: str, name: str, log: Log) -> dict:
    """Deletes the folder of a repository. The name is checked: nothing outside the storage is touched."""
    root = Path(storage_path).resolve()
    if not REPOSITORY_NAME.match(name) or name in IGNORED or name.startswith("."):
        log.add(f"{name}: refused, not a valid repository name.")
        return {"deleted": False, "size_bytes": 0, "archives": 0}
    repository = root / name
    if repository.is_symlink() or repository.resolve().parent != root or not (repository / "config").is_file():
        log.add(f"{name}: refused, not a Borg repository of this storage.")
        return {"deleted": False, "size_bytes": 0, "archives": 0}
    if is_in_use(repository):
        log.add(f"{name}: skipped, the repository is in use.")
        return {"deleted": False, "size_bytes": 0, "archives": 0}
    details = describe_repository(repository)
    try:
        shutil.rmtree(repository)
    except OSError as exception:
        log.add(f"{name}: ERROR {exception}")
        return {"deleted": False, "size_bytes": 0, "archives": 0}
    log.add(f"{name}: deleted ({details['archives']} backup(s), {details['size_bytes']} bytes, "
            f"last backup {details['last_backup'] or 'never'}).")
    return {"deleted": True, "size_bytes": details["size_bytes"], "archives": details["archives"]}


def celery_day_of_week(field: str) -> str:
    """Cron counts Sunday as 0 or 7, Celery only as 0. Lists and ranges (1-7) are expanded."""
    days: set[int] = set()
    for part in field.split(","):
        if part.isdigit():
            days.add(int(part) % 7)
        elif "-" in part and all(side.isdigit() for side in part.split("-", 1)):
            start, end = (int(side) for side in part.split("-", 1))
            days.update(day % 7 for day in range(start, end + 1))
        else:
            return field
    return ",".join(str(day) for day in sorted(days))


# Records of the cleanings

def create_run(storage: Storage, kind: str, trigger: str, user: str | None) -> UUID:
    with Session(get_engine()) as session:
        run = CleanupRun(storage_id=storage.id, storage_name=storage.name, kind=kind,
                         trigger=trigger, user=user)
        session.add(run)
        session.commit()
        return run.id


def finish_run(run_id: UUID, status: str, summary: dict, log: Log):
    with Session(get_engine()) as session:
        run = session.get(CleanupRun, run_id)
        run.status = status
        run.finished_at = now()
        run.summary = json.dumps(summary)
        run.log = log.text()
        session.add(run)
        session.commit()


def mark_interrupted() -> int:
    """A cleaning still running after a long time was stopped by a restart."""
    from datetime import timedelta
    limit = now() - timedelta(hours=INTERRUPTED_HOURS)
    with Session(get_engine()) as session:
        result = session.exec(update(CleanupRun)
                              .where(col(CleanupRun.status) == "running", col(CleanupRun.started_at) < limit)
                              .values(status="failed", finished_at=now()))
        session.commit()
        return result.rowcount or 0


def run_to_json(run: CleanupRun, with_log: bool = False) -> dict:
    def utc(value):
        if value is None:
            return None
        return (value if value.tzinfo else value.replace(tzinfo=timezone.utc)).isoformat()
    data = {
        "id": str(run.id), "storage_id": str(run.storage_id), "storage_name": run.storage_name,
        "kind": run.kind, "trigger": run.trigger, "user": run.user,
        "started_at": utc(run.started_at), "finished_at": utc(run.finished_at),
        "status": run.status, "summary": json.loads(run.summary) if run.summary else {},
    }
    if with_log:
        data["log"] = run.log or ""
    return data


def list_runs(limit: int, storage_id: UUID | None = None) -> list[dict]:
    statement = select(CleanupRun).order_by(col(CleanupRun.started_at).desc()).limit(limit)
    if storage_id:
        statement = statement.where(CleanupRun.storage_id == storage_id)
    with Session(get_engine()) as session:
        return [run_to_json(run) for run in session.exec(statement).all()]


def get_run(run_id: UUID) -> dict | None:
    with Session(get_engine()) as session:
        run = session.get(CleanupRun, run_id)
        return run_to_json(run, with_log=True) if run else None


def has_running_run(storage_id: UUID) -> bool:
    mark_interrupted()
    with Session(get_engine()) as session:
        return session.exec(select(CleanupRun).where(
            CleanupRun.storage_id == storage_id, CleanupRun.status == "running")).first() is not None


# Settings of a storage

def default_settings(storage: Storage) -> dict:
    return {"storage_id": str(storage.id), "storage_name": storage.name, "path": storage.path,
            "keep_days": DEFAULT_KEEP_DAYS, "after_backup": False, "scheduled": False,
            "schedule": DEFAULT_SCHEDULE, "hook_id": None}


def settings_to_json(storage: Storage, settings: StorageCleanup | None) -> dict:
    data = default_settings(storage)
    if settings:
        data.update({"keep_days": settings.keep_days, "after_backup": settings.after_backup,
                     "scheduled": settings.scheduled, "schedule": settings.schedule,
                     "hook_id": str(settings.hook_id) if settings.hook_id else None})
    return data


def get_settings(storage_id: UUID) -> StorageCleanup | None:
    with Session(get_engine()) as session:
        return session.get(StorageCleanup, storage_id)


def get_storage(storage_id: UUID) -> Storage | None:
    with Session(get_engine()) as session:
        return session.get(Storage, storage_id)


def get_storage_by_path(path: str) -> Storage | None:
    with Session(get_engine()) as session:
        return session.exec(select(Storage).where(Storage.path == path)).first()


def delete_settings(storage_id: UUID):
    with Session(get_engine()) as session:
        settings = session.get(StorageCleanup, storage_id)
        if settings is not None:
            session.delete(settings)
            session.commit()


def forget_hook(hook_id: UUID):
    """The hook is being deleted: the storages that used it do not notify anybody any more."""
    with Session(get_engine()) as session:
        for settings in session.exec(select(StorageCleanup).where(StorageCleanup.hook_id == hook_id)).all():
            settings.hook_id = None
            session.add(settings)
        session.commit()


def list_settings() -> list[dict]:
    with Session(get_engine()) as session:
        storages = session.exec(select(Storage)).all()
        saved = {item.storage_id: item for item in session.exec(select(StorageCleanup)).all()}
    return [settings_to_json(storage, saved.get(storage.id)) for storage in storages]


def check_settings(keep_days: int, schedule: str, hook_id: UUID | None):
    from croniter import croniter
    if not MIN_DAYS <= keep_days <= MAX_DAYS:
        raise ValueError(f"The number of days must be between {MIN_DAYS} and {MAX_DAYS}.")
    if not croniter.is_valid(schedule) or len(schedule.split()) != 5:
        raise ValueError("The schedule is not a valid cron expression of five fields.")
    if hook_id is not None:
        with Session(get_engine()) as session:
            if session.get(ExternalHooks, hook_id) is None:
                raise ValueError("The external hook does not exist.")


def save_settings(storage_id: UUID, keep_days: int, after_backup: bool, scheduled: bool,
                  schedule: str, hook_id: UUID | None) -> dict:
    check_settings(keep_days, schedule, hook_id)
    with Session(get_engine()) as session:
        storage = session.get(Storage, storage_id)
        if storage is None:
            raise LookupError("Storage not found.")
        settings = session.get(StorageCleanup, storage_id) or StorageCleanup(storage_id=storage_id)
        settings.keep_days, settings.after_backup = keep_days, after_backup
        settings.scheduled, settings.schedule, settings.hook_id = scheduled, schedule.strip(), hook_id
        session.add(settings)
        session.commit()
        session.refresh(settings)
        return settings_to_json(storage, settings)


def summary_text(summary: dict) -> str:
    freed = summary.get("freed_bytes", 0)
    return (f"{summary.get('archives_deleted', 0)} backup(s) deleted in "
            f"{summary.get('repositories', 0)} repository(ies), {notifier.human_size(freed)} freed, "
            f"{summary.get('errors', 0)} error(s).")


def notify(hook_id: UUID | None, text: str, blocks: list | None = None):
    """Best effort: a hook that does not answer never stops a cleaning."""
    notifier.send(hook_id, text, blocks)


def after_backup(storage_path: str, repository_name: str):
    """Right after the backup of a machine: its repository is cleaned if the storage asks for it.
    A problem here never fails the backup. Only a cleaning that did something is recorded."""
    try:
        storage = get_storage_by_path(storage_path)
        settings = get_settings(storage.id) if storage else None
        if not settings or not settings.after_backup or not REPOSITORY_NAME.match(repository_name):
            return
        log = Log()
        log.add(f"Cleaning of {repository_name} after its backup.")
        result = prune_repository(Path(storage_path) / repository_name, settings.keep_days, log)
        if result["archives_deleted"] or result["errors"]:
            summary = {"repositories": 1, **result}
            run_id = create_run(storage, "prune", "after_backup", None)
            finish_run(run_id, "failed" if result["errors"] else "success", summary, log)
    except Exception as exception:
        print(f"Unable to clean after the backup. {exception}")
