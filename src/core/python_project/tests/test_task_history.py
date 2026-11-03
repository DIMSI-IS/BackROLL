"""The history of the backups and restores in the database."""

import os
import time
from types import SimpleNamespace

import pytest

os.environ.setdefault("JWT_SECRET", "x" * 40)

from sqlmodel import Session, SQLModel, create_engine  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app import task_history  # noqa: E402
from app.database import TaskRun  # noqa: E402


@pytest.fixture(autouse=True)
def database(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(task_history, "get_engine", lambda: engine)
    return engine


def task(name):
    return SimpleNamespace(name=name)


VM = {"name": "web-01", "uuid": "11111111-1111-1111-1111-111111111111", "pool_id": "p1"}


def test_a_successful_backup_is_recorded():
    task_history.on_task_start(task_id="a", task=task("Single_VM_Backup"), args=[VM])
    assert task_history.list_runs(task_history.BACKUP_TASKS)["a"]["state"] == "STARTED"

    task_history.on_task_end(task_id="a", task=task("Single_VM_Backup"), state="SUCCESS")
    run = task_history.list_runs(task_history.BACKUP_TASKS)["a"]
    assert run["state"] == "SUCCESS"
    # The interface reads the machine in the arguments, in seconds.
    assert run["args"][0]["name"] == "web-01"
    assert run["succeeded"] is not None and run["failed"] is None
    assert run["runtime"] >= 0


def test_a_failure_keeps_its_error_and_stays_a_failure():
    task_history.on_task_start(task_id="b", task=task("backup_subtask"), args=[VM])
    task_history.on_task_failure(task_id="b", sender=task("backup_subtask"),
                                 exception=RuntimeError("Borg repository is locked"))
    # Celery then calls task_postrun with the state FAILURE.
    task_history.on_task_end(task_id="b", task=task("backup_subtask"), state="FAILURE")
    run = task_history.list_runs(task_history.BACKUP_TASKS)["b"]
    assert run["state"] == "FAILURE"
    assert "locked" in run["exception"]
    assert run["failed"] is not None


def test_only_backups_and_restores_are_recorded():
    task_history.on_task_start(task_id="c", task=task("List registered storage"), args=[])
    task_history.on_task_end(task_id="c", task=task("List registered storage"), state="SUCCESS")
    assert task_history.list_runs(task_history.BACKUP_TASKS | task_history.RESTORE_TASKS) == {}


def test_backups_and_restores_are_listed_apart():
    task_history.on_task_start(task_id="d", task=task("VM_Restore_Disk"), args=[VM])
    task_history.on_task_start(task_id="e", task=task("Single_VM_Backup"), args=[VM])
    assert set(task_history.list_runs(task_history.RESTORE_TASKS)) == {"d"}
    assert set(task_history.list_runs(task_history.BACKUP_TASKS)) == {"e"}


def test_what_flower_knows_wins_and_the_history_fills_the_rest():
    task_history.on_task_start(task_id="old", task=task("Single_VM_Backup"), args=[VM])
    task_history.on_task_end(task_id="old", task=task("Single_VM_Backup"), state="SUCCESS")
    task_history.on_task_start(task_id="both", task=task("Single_VM_Backup"), args=[VM])

    flower = {"both": {"uuid": "both", "state": "SUCCESS", "from": "flower"}}
    merged = task_history.merge(flower, task_history.BACKUP_TASKS)
    assert set(merged) == {"old", "both"}
    assert merged["both"]["from"] == "flower"
    assert merged["old"]["state"] == "SUCCESS"


def test_old_records_are_deleted(database):
    with Session(database) as session:
        session.add(TaskRun(id="ancient", name="Single_VM_Backup", state="SUCCESS",
                            started=time.time() - 200 * 86400))
        session.add(TaskRun(id="recent", name="Single_VM_Backup", state="SUCCESS", started=time.time()))
        session.commit()
    assert task_history.purge_old_runs(90) == 1
    assert set(task_history.list_runs(task_history.BACKUP_TASKS)) == {"recent"}


def test_a_failure_of_the_history_does_not_raise(monkeypatch):
    def broken():
        raise RuntimeError("database down")
    monkeypatch.setattr(task_history, "get_engine", broken)
    # Must not raise: a backup never fails because its history could not be written.
    task_history.on_task_start(task_id="x", task=task("Single_VM_Backup"), args=[VM])
    task_history.on_task_end(task_id="x", task=task("Single_VM_Backup"), state="SUCCESS")


def test_the_end_written_by_the_worker_wins_over_a_flower_that_is_late(database, monkeypatch):
    """Flower still says STARTED (an event came late or was lost): the interface must not show it forever."""
    task_history.on_task_start(task_id="late", task=task("Single_VM_Backup"), args=[VM])
    task_history.on_task_end(task_id="late", task=task("Single_VM_Backup"), state="SUCCESS")
    flower = {"late": {"uuid": "late", "state": "STARTED", "runtime": None, "name": "Single_VM_Backup"}}
    merged = task_history.merge(flower, task_history.BACKUP_TASKS)["late"]
    assert merged["state"] == "SUCCESS" and merged["runtime"] is not None

    # A task that is really running stays running.
    task_history.on_task_start(task_id="now", task=task("Single_VM_Backup"), args=[VM])
    flower = {"now": {"uuid": "now", "state": "STARTED", "runtime": None, "name": "Single_VM_Backup"}}
    assert task_history.merge(flower, task_history.BACKUP_TASKS)["now"]["state"] == "STARTED"


SKIPPED_RESULT = {"info": VM, "status": "skipped",
                  "reason": "The virtual machine is not running (state Stopped): it is not backed up."}


def test_a_backup_skipped_because_the_machine_is_off_is_not_shown_as_a_success():
    """Celery calls it a success, but nothing was copied: the history says it was skipped, with the reason."""
    task_history.on_task_start(task_id="off", task=task("Single_VM_Backup"), args=[VM])
    task_history.on_task_end(task_id="off", task=task("Single_VM_Backup"), state="SUCCESS", retval=SKIPPED_RESULT)
    run = task_history.list_runs(task_history.BACKUP_TASKS)["off"]
    assert run["state"] == "SKIPPED"
    assert "not running" in run["reason"]
    assert run["succeeded"] is None and run["failed"] is None


def test_a_real_success_and_a_result_without_status_stay_a_success():
    task_history.on_task_start(task_id="ok", task=task("Single_VM_Backup"), args=[VM])
    task_history.on_task_end(task_id="ok", task=task("Single_VM_Backup"), state="SUCCESS",
                             retval={"info": VM, "status": "success"})
    task_history.on_task_start(task_id="none", task=task("Single_VM_Backup"), args=[VM])
    task_history.on_task_end(task_id="none", task=task("Single_VM_Backup"), state="SUCCESS", retval=None)
    runs = task_history.list_runs(task_history.BACKUP_TASKS)
    assert runs["ok"]["state"] == "SUCCESS" and runs["ok"]["reason"] is None
    assert runs["none"]["state"] == "SUCCESS"


def test_the_skipped_state_wins_over_the_success_that_flower_reports():
    task_history.on_task_start(task_id="off", task=task("Single_VM_Backup"), args=[VM])
    task_history.on_task_end(task_id="off", task=task("Single_VM_Backup"), state="SUCCESS", retval=SKIPPED_RESULT)
    flower = {"off": {"uuid": "off", "state": "SUCCESS", "runtime": 0.1, "name": "Single_VM_Backup"}}
    merged = task_history.merge(flower, task_history.BACKUP_TASKS)["off"]
    assert merged["state"] == "SKIPPED"
    assert "not running" in merged["reason"]


def test_the_times_of_the_history_keep_their_precision():
    """MariaDB rounds a FLOAT to 7 digits (1792353940.19 becomes 1792350000): the columns are doubles."""
    from sqlalchemy import Float
    for column in (TaskRun.__table__.c.started, TaskRun.__table__.c.finished):
        assert isinstance(column.type, Float) and column.type.precision == 53
