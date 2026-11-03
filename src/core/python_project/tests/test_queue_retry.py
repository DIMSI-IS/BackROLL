"""A backup that waits for a free place must wait as long as needed: it is put back in the queue, not failed.

Found on the lab with three backups at once and a limit of one: the waiting ones failed after 45 seconds
(three retries of 15 seconds), because retry(max_retries=None) means the default of the task, not no limit.
"""

import os

import pytest

os.environ.setdefault("JWT_SECRET", "x" * 40)

pytest.importorskip("libvirt")

from app import backup_limit  # noqa: E402
from app.backup_tasks import pool_backup, single_backup  # noqa: E402


@pytest.mark.parametrize("task", [single_backup.single_vm_backup, pool_backup.backup_subtask])
def test_the_number_of_retries_is_not_limited(task):
    assert task.max_retries is None


@pytest.mark.parametrize("task,inner", [(single_backup.single_vm_backup, "run_single_vm_backup"),
                                         (pool_backup.backup_subtask, "run_backup_subtask")])
def test_a_backup_waits_more_than_three_turns_then_runs(monkeypatch, task, inner):
    module = single_backup if task is single_backup.single_vm_backup else pool_backup
    answers = iter([None] * 8 + ["slot"])
    monkeypatch.setattr(backup_limit, "try_acquire", lambda *_: next(answers))
    released = []
    monkeypatch.setattr(backup_limit, "release", released.append)
    monkeypatch.setattr(module, inner, lambda info: "done")
    result = task.apply(args=({"name": "machine"},))
    assert result.successful(), result.result
    assert result.result == "done"
    assert released == ["slot"]
