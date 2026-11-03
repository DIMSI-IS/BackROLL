"""A machine that is not running is not backed up: it is skipped, not failed (the production of DIMSI does not
back them up either). Only the running machines are sent to the workers."""

import inspect
import os

import pytest

os.environ.setdefault("JWT_SECRET", "x" * 40)

pytest.importorskip("libvirt")

from app import backup_limit  # noqa: E402
from app.backup_tasks import eligibility, pool_backup, single_backup  # noqa: E402
from app.routes import kickstart_backup  # noqa: E402


@pytest.mark.parametrize("state", ["Stopped", "Shutoff", "Shutdown", "Starting", "Stopping", "Paused", "Unknown"])
def test_a_machine_that_is_not_running_is_skipped(state):
    result = eligibility.skipped({"name": "i-1-VM", "state": state})
    assert result["status"] == "skipped" and state in result["reason"]


@pytest.mark.parametrize("info", [{"name": "i-1-VM", "state": "Running"}, {"name": "i-1-VM"}, "not a dict"])
def test_a_running_machine_or_an_unknown_state_is_not_skipped(info):
    assert eligibility.skipped(info) is None


@pytest.mark.parametrize("task,inner", [(single_backup.single_vm_backup, "run_single_vm_backup"),
                                         (pool_backup.backup_subtask, "run_backup_subtask")])
def test_a_skipped_machine_takes_no_place_and_copies_nothing(monkeypatch, task, inner):
    module = single_backup if task is single_backup.single_vm_backup else pool_backup
    calls = []
    monkeypatch.setattr(backup_limit, "try_acquire", lambda *args: calls.append("place") or "slot")
    monkeypatch.setattr(module, inner, lambda info: calls.append("backup"))
    result = task.apply(args=({"name": "i-1-VM", "state": "Stopped"},))
    assert result.successful()
    assert result.result["status"] == "skipped"
    assert calls == []


def test_the_powered_off_machines_of_cloudstack_are_not_added_to_the_pool_backups():
    source = inspect.getsource(kickstart_backup.getVMtobackup)
    assert "listPoweredOffVms" not in source
    assert "'Running'" in source or '"Running"' in source
