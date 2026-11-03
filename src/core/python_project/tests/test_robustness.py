"""The lock of a machine, the restore that fails after the machine was stopped, and the hypervisors of a pool that
could not be backed up.

Found by the review of the code: the lock was taken in three steps (two tasks could both pass; a task that died
between two steps left a lock that never ended) and the restore used another key than the backups; a restore that
failed left the machine stopped and a partial file; a hypervisor that did not answer was skipped without a word.
"""

import os
import shutil
from types import SimpleNamespace
from uuid import uuid4

import pytest

os.environ.setdefault("JWT_SECRET", "x" * 40)

from app import backup_limit  # noqa: E402


class FakeRedis:
    """Only what the lock uses. `set` with nx is one operation, as in Redis."""

    def __init__(self):
        self.values = {}
        self.calls = []

    def set(self, key, value, nx=False, ex=None):
        self.calls.append((key, nx, ex))
        if nx and key in self.values:
            return None
        self.values[key] = (value, ex)
        return True

    def exists(self, key):
        return key in self.values

    def delete(self, key):
        self.values.pop(key, None)

    def expire(self, key, seconds):  # the old way: a second step, never used any more
        raise AssertionError("the expiry must be given by the same command that takes the lock")

    def quit(self):
        pass


VM = {"uuid": "11111111-1111-1111-1111-111111111111", "name": "web-01", "state": "Running", "host": "h1"}


# -- the lock -----------------------------------------------------------------------------------------------------

def test_the_lock_is_taken_and_given_its_expiry_by_one_command():
    redis = FakeRedis()
    key = backup_limit.acquire_vm_lock(redis, VM)
    assert key == f"vmlock-{VM['uuid']}"
    # One call, with the "only if free" flag and the expiry: nothing in between where a task could die.
    assert redis.calls == [(key, True, backup_limit.VM_LOCK_SECONDS)]


def test_a_machine_that_is_locked_can_not_be_locked_again():
    redis = FakeRedis()
    assert backup_limit.acquire_vm_lock(redis, VM) is not None
    assert backup_limit.acquire_vm_lock(redis, VM) is None


def test_the_lock_does_not_depend_on_what_changes_in_the_description_of_the_machine():
    redis = FakeRedis()
    assert backup_limit.acquire_vm_lock(redis, VM) is not None
    # The state, the pool... change from one call to the next: it is the same machine.
    assert backup_limit.acquire_vm_lock(redis, {**VM, "state": "Shutoff", "pool_id": "p9"}) is None


def test_a_backup_does_not_start_on_a_machine_that_is_locked(monkeypatch):
    pytest.importorskip("libvirt")
    from app.backup_tasks import single_backup, pool_backup
    for module, call in ((single_backup, lambda: single_backup.run_single_vm_backup(VM)),
                         (pool_backup, lambda: pool_backup.run_backup_subtask(VM))):
        redis = FakeRedis()
        backup_limit.acquire_vm_lock(redis, VM)
        started = []
        monkeypatch.setattr(module, "new_redis_client", lambda redis=redis: redis)
        if hasattr(module, "backup_creation"):
            monkeypatch.setattr(module, "backup_creation", lambda info: started.append(info))
        with pytest.raises(ValueError, match="already running"):
            call()
        assert started == []


def test_the_lock_is_given_back_after_a_backup_and_after_a_failure(monkeypatch):
    pytest.importorskip("libvirt")
    from app.backup_tasks import single_backup
    redis = FakeRedis()
    monkeypatch.setattr(single_backup, "new_redis_client", lambda: redis)
    monkeypatch.setattr(single_backup, "backup_creation", lambda info: "done")
    assert single_backup.run_single_vm_backup(VM) == "done"
    assert redis.values == {}

    def broken(info):
        raise RuntimeError("borg failed")
    monkeypatch.setattr(single_backup, "backup_creation", broken)
    with pytest.raises(RuntimeError):
        single_backup.run_single_vm_backup(VM)
    assert redis.values == {}


def test_a_restore_does_not_start_during_a_backup_of_the_machine(monkeypatch):
    pytest.importorskip("libvirt")
    from app import restore
    redis = FakeRedis()
    # The lock that a backup of this machine holds.
    backup_limit.acquire_vm_lock(redis, VM)
    monkeypatch.setattr(restore, "new_redis_client", lambda: redis)
    with pytest.raises(ValueError, match="already running"):
        restore.restore_disk_vm.run(VM, "vda_x_1792000000", "", "")


# -- a restore that fails -----------------------------------------------------------------------------------------

KVM_VM = {"name": "web-01", "uuid": "vm-1", "host": "h1", "pool_id": "p1", "cloudstack_instance": False}
DISKS = [{"device": "vda", "source": "/var/lib/libvirt/images/a.qcow2"}]


def restore_environment(monkeypatch, tmp_path, commands, fail_on=None):
    pytest.importorskip("libvirt")
    from app import file_browser, restore
    monkeypatch.setattr(restore.storage, "retrieveStoragePathFromHostBackupPolicy", lambda info: {"path": str(tmp_path)})
    monkeypatch.setattr(restore.shell, "subprocess_run", lambda command: commands.append(command) or "")
    monkeypatch.setattr(restore.shell, "subprocess_popen", lambda command: commands.append(command) or "")

    def os_system(command):
        commands.append(command)
        if fail_on and command.startswith(fail_on):
            raise restore.shell.ShellException(1)
    monkeypatch.setattr(restore.shell, "os_system", os_system)
    monkeypatch.setattr(restore.os, "chdir", lambda path: None)
    monkeypatch.setattr(restore, "is_nfs", lambda path: True)
    monkeypatch.setattr(file_browser, "archive_size", lambda *arguments: 1)
    monkeypatch.setattr(file_browser, "check_free_space", lambda *arguments: None)
    monkeypatch.setattr(restore.pool, "filter_pool_by_id", lambda pool_id: SimpleNamespace(connector_id=None))
    events = []
    monkeypatch.setattr(restore.kvm_manage_vm, "stop_vm", lambda *arguments: events.append("stop"))
    monkeypatch.setattr(restore.kvm_manage_vm, "start_vm", lambda *arguments: events.append("start"))
    return restore, events


def test_a_restore_that_fails_while_copying_starts_the_machine_again_and_removes_the_partial_copy(monkeypatch, tmp_path):
    commands = []
    restore, events = restore_environment(monkeypatch, tmp_path, commands, fail_on="cp ")

    with pytest.raises(restore.shell.ShellException):
        restore.restore_task(None, KVM_VM, {"pool_id": "p1"}, DISKS, "vda_x_1792000000")

    # Stopped for the copy, then started again although the copy failed: the old disk is still in place.
    assert events == ["stop", "start"]
    assert any(command.startswith("rm -f ") and command.endswith("a.qcow2.tmp") for command in commands)
    # The disk was never replaced.
    assert not any(command.startswith("mv ") and command.endswith("a.qcow2") for command in commands)


def test_a_restore_that_works_stops_then_starts_the_machine_once(monkeypatch, tmp_path):
    commands = []
    restore, events = restore_environment(monkeypatch, tmp_path, commands)
    restore.restore_task(None, KVM_VM, {"pool_id": "p1"}, DISKS, "vda_x_1792000000")
    assert events == ["stop", "start"]
    assert not any(command.startswith("rm -f ") for command in commands)


def test_a_restore_without_room_to_replace_the_disk_does_not_stop_the_machine(monkeypatch, tmp_path):
    commands = []
    restore, events = restore_environment(monkeypatch, tmp_path, commands)
    monkeypatch.setattr(restore, "extracted_size", lambda name: 50 * 1024 ** 3)
    monkeypatch.setattr(shutil, "disk_usage", lambda path: SimpleNamespace(free=5 * 1024 ** 3))

    with pytest.raises(ValueError, match="Not enough free space where the disk is replaced"):
        restore.restore_task(None, KVM_VM, {"pool_id": "p1"}, DISKS, "vda_x_1792000000")

    assert events == []
    assert not any(".tmp" in command for command in commands)


def test_a_missing_extracted_file_does_not_block_the_room_check(monkeypatch, tmp_path):
    pytest.importorskip("libvirt")
    from app import restore
    assert restore.extracted_size(str(tmp_path / "nothing.qcow2")) == 0


# -- the hypervisors of a pool ------------------------------------------------------------------------------------

@pytest.fixture
def pool_world(monkeypatch):
    pytest.importorskip("libvirt")
    from sqlalchemy.pool import StaticPool
    from sqlmodel import Session, SQLModel, create_engine

    from app.database import Hosts
    from app.routes import backup_policy, kickstart_backup

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    pool_id = uuid4()
    with Session(engine) as session:
        session.add(Hosts(hostname="kvm-ok", ipaddress="10.0.0.1", ssh=True, pool_id=pool_id))
        session.add(Hosts(hostname="kvm-down", ipaddress="10.0.0.2", ssh=True, pool_id=pool_id))
        session.add(Hosts(hostname="kvm-new", ipaddress="10.0.0.3", ssh=False, pool_id=pool_id))
        session.commit()
    monkeypatch.setattr(kickstart_backup.database, "init_db_connection", lambda: engine)

    def os_system(command):
        if "10.0.0.2" in command:
            raise kickstart_backup.shell.ShellException(1)
    monkeypatch.setattr(kickstart_backup.shell, "os_system", os_system)
    sent = []
    monkeypatch.setattr(kickstart_backup.notifier, "send", lambda hook_id, text, blocks=None: sent.append((hook_id, text, blocks)))
    monkeypatch.setattr(kickstart_backup.pool, "filter_pool_by_id", lambda identifier: SimpleNamespace(name="production", policy_id="p"))
    monkeypatch.setattr(backup_policy, "filter_policy_by_id", lambda identifier: SimpleNamespace(externalhook="hook-1"))
    return kickstart_backup, str(pool_id), sent


def test_a_hypervisor_that_is_down_or_not_connected_is_told_to_the_hook_and_the_others_are_backed_up(monkeypatch, pool_world):
    kickstart_backup, pool_id, sent = pool_world
    monkeypatch.setattr(kickstart_backup.kvm_manage_vm, "retrieve_virtualmachine",
                        lambda host: [{"name": "web-01", "state": "Running", "id": 3}])

    machines = kickstart_backup.getVMtobackup(pool_id)

    # What is backed up does not change: the machines of the hypervisor that answers.
    assert [machine["name"] for machine in machines] == ["web-01"]
    assert len(sent) == 1
    hook_id, text, blocks = sent[0]
    assert hook_id == "hook-1" and "<!channel>" in text and "production" in text
    assert "kvm-down" in text and "port 22" in text
    assert "kvm-new" in text and "not connected" in text
    assert "kvm-ok" not in text
    assert "other hypervisors are backed up" in text
    assert blocks


def test_a_hypervisor_whose_machines_can_not_be_listed_is_told_and_the_pool_still_stops_as_before(monkeypatch, pool_world):
    kickstart_backup, pool_id, sent = pool_world

    def broken(host):
        raise RuntimeError("libvirt: connection refused")
    monkeypatch.setattr(kickstart_backup.kvm_manage_vm, "retrieve_virtualmachine", broken)

    with pytest.raises(RuntimeError):
        kickstart_backup.getVMtobackup(pool_id)

    assert len(sent) == 1
    assert "kvm-ok" in sent[0][1] and "could not be listed" in sent[0][1] and "did not start" in sent[0][1]


def test_nothing_is_told_when_every_hypervisor_is_fine(monkeypatch, pool_world):
    kickstart_backup, pool_id, sent = pool_world
    monkeypatch.setattr(kickstart_backup.shell, "os_system", lambda command: None)
    from sqlmodel import Session, select

    from app.database import Hosts
    with Session(kickstart_backup.database.init_db_connection()) as session:
        for host in session.exec(select(Hosts)).all():
            host.ssh = True
            session.add(host)
        session.commit()
    monkeypatch.setattr(kickstart_backup.kvm_manage_vm, "retrieve_virtualmachine", lambda host: [])
    kickstart_backup.getVMtobackup(pool_id)
    assert sent == []


def test_a_hook_that_fails_never_changes_what_the_pool_does(monkeypatch, pool_world):
    kickstart_backup, pool_id, sent = pool_world

    def broken(*arguments, **keywords):
        raise ConnectionError("slack is down")
    monkeypatch.setattr(kickstart_backup.notifier, "send", broken)
    monkeypatch.setattr(kickstart_backup.kvm_manage_vm, "retrieve_virtualmachine",
                        lambda host: [{"name": "web-01", "state": "Running", "id": 3}])
    assert [machine["name"] for machine in kickstart_backup.getVMtobackup(pool_id)] == ["web-01"]
