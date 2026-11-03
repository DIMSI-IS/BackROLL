"""History of the backups and restores, kept in the database.

Flower, which lists the tasks in the interface, keeps them in memory: they are lost each time its
container is recreated. The worker records here each backup and restore when it starts and ends,
and the lists of the interface add these records to what Flower knows.
"""

import json
import time
from datetime import datetime, timedelta, timezone

from celery.signals import task_failure, task_postrun, task_prerun
from sqlmodel import Session, col, delete, select

from app.auth.password import get_engine
from app.database import TaskRun
from app import settings

BACKUP_TASKS = {"Single_VM_Backup", "backup_subtask"}
RESTORE_TASKS = {"VM_Restore_Disk"}
TRACKED = BACKUP_TASKS | RESTORE_TASKS
SKIPPED = "SKIPPED"
MAX_TEXT = 20000


def _safe(action):
    """A failure of the history must never fail a backup."""
    def wrapper(*args, **kwargs):
        try:
            return action(*args, **kwargs)
        except Exception as exception:
            print(f"Unable to record the task history. {exception}")
    return wrapper


def record_start(task_id: str, name: str, args) -> None:
    text = json.dumps(args if args is not None else [], default=str)[:MAX_TEXT]
    with Session(get_engine()) as session:
        run = session.get(TaskRun, task_id) or TaskRun(id=task_id, name=name, started=time.time())
        # A task that waited for a free place (RETRY) starts now: its duration is the one of the backup.
        run.started = time.time()
        run.finished = None
        run.error = None
        run.state = "STARTED"
        run.args = text
        session.add(run)
        session.commit()


def record_end(task_id: str, name: str, state: str | None, error: str | None = None) -> None:
    with Session(get_engine()) as session:
        run = session.get(TaskRun, task_id) or TaskRun(id=task_id, name=name, started=time.time())
        if error:
            run.error = error[:MAX_TEXT]
        # task_failure comes before task_postrun: a failure is not turned back into a success.
        if run.state != "FAILURE" or state == "FAILURE":
            run.state = state or run.state
        # A task that goes back to the queue is waiting, not finished.
        run.finished = None if state == "RETRY" else time.time()
        session.add(run)
        session.commit()


@task_prerun.connect
@_safe
def on_task_start(sender=None, task_id=None, task=None, args=None, **kwargs):
    if task is not None and task.name in TRACKED:
        record_start(task_id, task.name, args)


@task_failure.connect
@_safe
def on_task_failure(sender=None, task_id=None, exception=None, **kwargs):
    if sender is not None and sender.name in TRACKED:
        record_end(task_id, sender.name, "FAILURE", str(exception))


def skipped_reason(result) -> str | None:
    """The reason of a backup that was not made because the machine is not running, else None."""
    if isinstance(result, dict) and result.get("status") == "skipped":
        return str(result.get("reason") or "The virtual machine is not running.")
    return None


@task_postrun.connect
@_safe
def on_task_end(sender=None, task_id=None, task=None, state=None, retval=None, **kwargs):
    if task is not None and task.name in TRACKED:
        # Celery calls it a success: nothing was copied, the interface must not say a backup was made.
        reason = skipped_reason(retval) if state == "SUCCESS" else None
        record_end(task_id, task.name, SKIPPED if reason else state, reason)


def list_runs(names: set[str]) -> dict[str, dict]:
    """The records, shaped like the tasks of Flower, which is what the interface reads."""
    with Session(get_engine()) as session:
        runs = session.exec(select(TaskRun).where(col(TaskRun.name).in_(names))
                            .order_by(col(TaskRun.started).desc()).limit(1000)).all()
    tasks = {}
    for run in runs:
        try:
            args = json.loads(run.args) if run.args else []
        except ValueError:
            args = []
        tasks[run.id] = {
            "uuid": run.id,
            "name": run.name,
            "state": run.state,
            "received": run.started,
            "started": run.started,
            "succeeded": run.finished if run.state == "SUCCESS" else None,
            "failed": run.finished if run.state == "FAILURE" else None,
            "runtime": (run.finished - run.started) if run.finished else None,
            "args": args,
            "exception": run.error,
            "reason": run.error if run.state == SKIPPED else None,
            "ip_address": None,
            "history": True,
        }
    return tasks


TERMINAL = ("SUCCESS", "FAILURE", SKIPPED)


def merge(flower_tasks: dict, names: set[str]) -> dict:
    """What Flower knows wins: it has the details of the tasks it saw. Except for the end of a task:
    Flower learns it from events that can come late or be lost, the worker wrote it down itself."""
    recorded = list_runs(names)
    merged = dict(recorded)
    for task_id, task in flower_tasks.items():
        run = recorded.get(task_id)
        if run and run["state"] == SKIPPED:
            # Flower sees a success: the worker knows that nothing was copied.
            task = {**task, "state": SKIPPED, "runtime": run["runtime"], "reason": run["reason"]}
        elif run and run["state"] in TERMINAL and task.get("state") not in TERMINAL:
            task = {**task, "state": run["state"], "runtime": run["runtime"],
                    "succeeded": run["succeeded"], "failed": run["failed"], "exception": run["exception"]}
        merged[task_id] = task
    return merged


def purge_old_runs(days: int | None = None) -> int:
    limit = (datetime.now(timezone.utc) - timedelta(days=days or settings.get_task_history_retention_days())).timestamp()
    with Session(get_engine()) as session:
        result = session.exec(delete(TaskRun).where(col(TaskRun.started) < limit))
        session.commit()
        return result.rowcount or 0
