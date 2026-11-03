"""Non-regression of the incident of a block commit that left a machine on its overlay file, whose overlay was then
deleted while the machine still wrote in it (see the report of the incident).

Each case ends in a verified success, or in NEEDS_ATTENTION with nothing deleted. A fake libvirt plays what the
hypervisor answers; the database is the SQLite of the tests.
"""

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, select

pytest.importorskip("libvirt")

from app import backup_limit, disk_state  # noqa: E402
from app.auth import password  # noqa: E402
from app.borg import borg_core  # noqa: E402
from app.database import DiskBackupState, User, init_db_connection, migrate_user_table  # noqa: E402
from app.initialized import fastapi_app  # noqa: E402
from app.kvm import disk_safety, kvm_manage_snapshot  # noqa: E402
from app.kvm.disk_safety import BackupStateError  # noqa: E402
from app.routes import attention  # noqa: E402,F401
from app.routes.auth import password as password_routes  # noqa: E402,F401

BASE = "/mnt/primary/vol-1"
SNAP = f"{BASE}.snap"


class LibvirtFailure(disk_safety.LibvirtError):
    def __init__(self, message, code=None):
        Exception.__init__(self, message)
        self.code = code

    def get_error_code(self):
        return self.code


class FakeDom:
    """A machine with disks. `chains` maps a device to [the file written, its backing files...]."""

    def __init__(self, chains, running=None, not_ready=0, pivot_moves=True, job_error=None):
        self.chains = {device: list(chain) for device, chain in chains.items()}
        self.job = running          # a job that already runs: what blockJobInfo answers (a dict or a list)
        self.after = None           # what blockJobInfo answers once the commit started
        self.not_ready = not_ready  # how many times the pivot answers "not ready" before it works
        self.pivot_moves = pivot_moves
        self.job_error = job_error
        self.commits, self.aborts = [], []

    def XMLDesc(self, flags):
        disks = ""
        for device, chain in self.chains.items():
            nested = ""
            for path in reversed(chain[1:]):
                nested = f"<backingStore type='file'><source file='{path}'/>{nested}</backingStore>"
            disks += f"<disk type='file'><source file='{chain[0]}'/><target dev='{device}'/>{nested}</disk>"
        return f"<domain><devices>{disks}</devices></domain>"

    def blockJobInfo(self, device, flags=0):
        if self.job_error:
            raise self.job_error
        if isinstance(self.job, list):
            return self.job.pop(0) if len(self.job) > 1 else self.job[0]
        return self.job or {}

    def blockCommit(self, device, base, top, bandwidth, flags):
        self.commits.append((device, base, top, flags))
        self.job = self.after if self.after is not None else {"cur": 5, "end": 10}

    def blockJobAbort(self, device, flags):
        self.aborts.append((device, flags))
        if flags != disk_safety.ABORT_PIVOT:
            return
        if self.not_ready > 0:
            self.not_ready -= 1
            raise LibvirtFailure("block job 'vdb' not ready for pivot yet", disk_safety.ERR_BLOCK_COPY_ACTIVE)
        if self.pivot_moves:
            self.chains[device] = self.chains[device][1:]
        self.job = {}


def fast(**more):
    return {"sleep": lambda seconds: None, **more}


def on_overlay(device="vdb"):
    return FakeDom({device: [SNAP, BASE]})


# -- the commit and the pivot ----------------------------------------------------------------------------------

def test_the_pivot_is_asked_again_until_the_job_is_ready():
    dom = on_overlay()
    dom.after = [{"cur": 5, "end": 10}, {"cur": 10, "end": 10}]
    dom.not_ready = 3
    disk_safety.commit_and_pivot(dom, "vdb", BASE, SNAP, **fast())
    pivots = [call for call in dom.aborts if call[1] == disk_safety.ABORT_PIVOT]
    assert len(pivots) == 4
    assert dom.chains["vdb"][0] == BASE
    # The commit asks libvirt to delete the overlay itself once it is pivoted: the code deletes nothing.
    assert dom.commits == [("vdb", BASE, SNAP, disk_safety.COMMIT_ACTIVE | disk_safety.COMMIT_DELETE)]


def test_the_pivot_is_not_asked_before_the_job_has_copied_everything():
    dom = on_overlay()
    dom.after = [{"cur": 1, "end": 10}, {"cur": 9, "end": 10}, {"cur": 10, "end": 10}]
    disk_safety.commit_and_pivot(dom, "vdb", BASE, SNAP, **fast())
    assert len(dom.aborts) == 1


def test_a_job_that_vanished_while_the_machine_is_on_its_base_is_a_success():
    dom = on_overlay()
    original = dom.blockCommit

    def commit_then_pivot(*args):
        original(*args)
        dom.job = {}
        dom.chains["vdb"] = [BASE]
    dom.blockCommit = commit_then_pivot
    disk_safety.commit_and_pivot(dom, "vdb", BASE, SNAP, **fast())
    assert dom.chains["vdb"][0] == BASE


def test_a_job_that_vanished_while_the_machine_is_on_the_overlay_needs_attention():
    dom = on_overlay()
    original = dom.blockCommit

    def commit_then_vanish(*args):
        original(*args)
        dom.job = {}
    dom.blockCommit = commit_then_vanish
    with pytest.raises(BackupStateError, match="still on"):
        disk_safety.commit_and_pivot(dom, "vdb", BASE, SNAP, **fast())
    assert dom.chains["vdb"][0] == SNAP


def test_a_commit_that_does_not_end_is_left_running_never_cancelled():
    dom = on_overlay()
    dom.after = {"cur": 1, "end": 10}
    ticks = iter(range(0, 100000, 1000))
    with pytest.raises(BackupStateError, match="left running"):
        disk_safety.commit_and_pivot(dom, "vdb", BASE, SNAP, timeout=10, clock=lambda: next(ticks), **fast())
    assert dom.aborts == []


def test_a_machine_stopped_or_moved_during_the_commit_needs_attention():
    dom = on_overlay()
    original = dom.blockCommit

    def commit_then_lose(*args):
        original(*args)
        dom.job_error = LibvirtFailure("Domain not found: no domain with matching name")
    dom.blockCommit = commit_then_lose
    with pytest.raises(BackupStateError, match="libvirt"):
        disk_safety.commit_and_pivot(dom, "vdb", BASE, SNAP, **fast())
    assert dom.aborts == []


def test_a_restart_of_libvirtd_is_decided_by_the_xml():
    # The connection is lost: nothing can be said, the machine is reported and left as it is.
    lost = on_overlay()
    lost.job_error = LibvirtFailure("internal error: client socket is closed")
    with pytest.raises(BackupStateError):
        disk_safety.commit_and_pivot(lost, "vdb", BASE, SNAP, **fast())
    # Asked again, the XML shows the machine on its base file: it is a success, nothing to commit.
    healthy = FakeDom({"vdb": [BASE]})
    disk_safety.commit_and_pivot(healthy, "vdb", BASE, SNAP, **fast())
    assert healthy.commits == []


def test_a_pivot_that_is_not_confirmed_by_the_xml_needs_attention():
    dom = on_overlay()
    dom.after = {"cur": 10, "end": 10}
    dom.pivot_moves = False
    with pytest.raises(BackupStateError, match="not confirmed"):
        disk_safety.commit_and_pivot(dom, "vdb", BASE, SNAP, **fast())


def test_a_block_job_that_is_already_running_is_not_taken_over():
    dom = on_overlay()
    dom.job = {"cur": 3, "end": 10}  # started by somebody else, before this run
    with pytest.raises(BackupStateError, match="already running"):
        disk_safety.commit_and_pivot(dom, "vdb", BASE, SNAP, **fast())
    assert dom.commits == [] and dom.aborts == []


# -- the checks before the backup -----------------------------------------------------------------------------------

def test_a_machine_that_is_already_on_an_overlay_is_refused():
    with pytest.raises(BackupStateError, match="overlay"):
        disk_safety.preflight(on_overlay(), "vdb")


def test_a_machine_with_a_running_job_is_refused():
    dom = FakeDom({"vdb": [BASE]}, running={"cur": 1, "end": 5})
    with pytest.raises(BackupStateError, match="block job"):
        disk_safety.preflight(dom, "vdb")


def test_a_clean_disk_gives_its_base_file():
    assert disk_safety.preflight(FakeDom({"vdb": [BASE]}), "vdb") == BASE


# -- the cleaning never touches a file that is used -----------------------------------------------------------------

class Hypervisor:
    def __init__(self, fuser_rc=1, mv_rc=0):
        self.commands, self.fuser_rc, self.mv_rc = [], fuser_rc, mv_rc

    def __call__(self, command):
        self.commands.append(command)
        return {"rc": self.fuser_rc if command.startswith("fuser") else self.mv_rc}


def test_an_overlay_listed_in_the_xml_is_never_touched():
    hypervisor = Hypervisor()
    with pytest.raises(BackupStateError, match="in use"):
        disk_safety.safe_remove(on_overlay(), SNAP, hypervisor)
    assert hypervisor.commands == []


@pytest.mark.parametrize("fuser_rc,expected", [(0, "open by a process"), (2, "could not be checked"),
                                                (127, "could not be checked")])
def test_an_overlay_that_a_process_holds_or_that_can_not_be_checked_is_not_moved(fuser_rc, expected):
    hypervisor = Hypervisor(fuser_rc=fuser_rc)
    with pytest.raises(BackupStateError, match=expected):
        disk_safety.safe_remove(FakeDom({"vdb": [BASE]}), SNAP, hypervisor)
    assert not any(command.startswith("mv") or command.startswith("rm") for command in hypervisor.commands)


def test_a_free_leftover_is_put_aside_not_deleted():
    hypervisor = Hypervisor(fuser_rc=1)
    moved = disk_safety.safe_remove(FakeDom({"vdb": [BASE]}), SNAP, hypervisor)
    assert moved.startswith(f"{SNAP}.trash-")
    assert hypervisor.commands[-1].startswith("mv -n ")
    assert not any(" rm " in f" {command} " for command in hypervisor.commands)


def test_the_backup_code_has_no_way_to_delete_a_file_of_the_machine():
    sources = [Path(borg_core.__file__), Path(disk_safety.__file__), Path(kvm_manage_snapshot.__file__)]
    for source in sources:
        text = source.read_text(encoding="utf-8")
        for forbidden in ("os.remove", ".unlink(", "shutil.rmtree", "rm -f", "rm -rf"):
            assert forbidden not in text, f"{forbidden} in {source.name}"


# -- the state of each disk, the machine that waits ---------------------------------------------------------------

@pytest.fixture
def database():
    engine = init_db_connection()
    SQLModel.metadata.create_all(engine)
    migrate_user_table(engine)
    with Session(engine) as session:
        for row in session.exec(select(DiskBackupState)).all():
            session.delete(row)
        session.commit()
    return engine


def test_a_disk_that_fails_is_recorded_alone_and_the_healthy_one_is_not(database):
    dom = FakeDom({"vda": [BASE.replace("vol-1", "vol-a")], "vdb": [SNAP, BASE]}, running={"cur": 2, "end": 10})
    disks = [{"device": "vda", "source": BASE.replace("vol-1", "vol-a")}, {"device": "vdb", "source": SNAP}]
    disk_state.set_step("vm-1", "i-1-VM", "vda", disk_state.CLEANED)

    def record(device, message):
        disk_state.set_step("vm-1", "i-1-VM", device, disk_state.NEEDS_ATTENTION, message)

    failed = disk_safety.recover_disks(dom, disks, record, **fast())
    assert failed == ["vdb"]
    waiting = disk_state.attention_of("vm-1")
    assert [row["disk"] for row in waiting] == ["vdb"]
    assert "already running" in waiting[0]["message"]
    # Nothing was cancelled or committed on top of the job that runs.
    assert dom.aborts == [] and dom.commits == []


def test_a_failed_backup_brings_the_machine_back_on_its_disks_when_it_can(database):
    dom = on_overlay()
    dom.after = {"cur": 10, "end": 10}
    failed = disk_safety.recover_disks(dom, [{"device": "vdb", "source": SNAP}], lambda *args: None, **fast())
    assert failed == [] and dom.chains["vdb"][0] == BASE


def test_the_lock_of_a_machine_does_not_depend_on_the_rest_of_the_task():
    first = {"uuid": "abc", "name": "i-1-VM", "state": "Running"}
    second = {"uuid": "abc", "name": "i-1-VM", "state": "Stopped", "pool_id": "p"}
    assert backup_limit.vm_lock_key(first) == backup_limit.vm_lock_key(second)
    assert backup_limit.vm_lock_key(first) != backup_limit.vm_lock_key({"uuid": "other", "name": "i-2-VM"})


# -- the check before a backup, with the real class of the backup -----------------------------------------------

class FakeConnection:
    closed = False

    def close(self):
        self.closed = True


def backup_job(monkeypatch, dom, uuid="vm-pre", disks=None):
    job = borg_core.borg_backup({"name": "i-pre-VM", "uuid": uuid}, None)
    job.vm_name = "i-pre-VM"
    job.info["host_info"] = {}
    job.virtual_machine = {"name": "i-pre-VM", "storage": disks or [{"device": "vdb", "source": BASE}]}
    monkeypatch.setattr(kvm_manage_snapshot, "open_domain", lambda *args: (FakeConnection(), dom))
    job.check_if_snapshot = lambda: False
    return job


def test_a_machine_on_an_overlay_is_refused_and_then_blocked_until_cleared(database, monkeypatch):
    job = backup_job(monkeypatch, on_overlay(), uuid="vm-snap")
    with pytest.raises(BackupStateError, match="NEEDS ATTENTION"):
        job.preflight()
    assert [row["disk"] for row in disk_state.attention_of("vm-snap")] == ["vdb"]

    # The next run does not even ask the hypervisor: the machine waits for an administrator.
    def forbidden(*args):
        raise AssertionError("the hypervisor must not be asked")
    monkeypatch.setattr(kvm_manage_snapshot, "open_domain", forbidden)
    with pytest.raises(BackupStateError, match="blocked until an administrator clears it"):
        job.preflight()

    assert disk_state.clear("vm-snap") == 1
    monkeypatch.setattr(kvm_manage_snapshot, "open_domain", lambda *args: (FakeConnection(), FakeDom({"vdb": [BASE]})))
    job.preflight()
    assert disk_state.attention_of("vm-snap") == []


def test_a_leftover_overlay_file_stops_the_backup_and_is_kept(database, monkeypatch, tmp_path):
    base = str(tmp_path / "vol-2")
    leftover = Path(base + ".snap")
    leftover.write_bytes(b"recent writes of the machine")
    job = backup_job(monkeypatch, FakeDom({"vdb": [base]}), uuid="vm-left", disks=[{"device": "vdb", "source": base}])
    with pytest.raises(BackupStateError, match="left on the storage"):
        job.preflight()
    assert leftover.read_bytes() == b"recent writes of the machine"
    assert disk_state.attention_of("vm-left")


def test_a_clean_machine_passes_and_each_step_is_recorded(database, monkeypatch):
    job = backup_job(monkeypatch, FakeDom({"vdb": [BASE]}), uuid="vm-ok")
    job.preflight()
    with Session(database) as session:
        assert session.get(DiskBackupState, ("vm-ok", "vdb")).step == disk_state.PRECHECK_OK


def test_a_failure_after_the_snapshot_never_deletes_the_overlay(database, monkeypatch, tmp_path):
    base = str(tmp_path / "vol-3")
    overlay = Path(base + ".snap")
    overlay.write_bytes(b"written while the backup ran")
    dom = FakeDom({"vdb": [overlay.as_posix(), base]}, running={"cur": 1, "end": 9})
    job = backup_job(monkeypatch, dom, uuid="vm-fail", disks=[{"device": "vdb", "source": overlay.as_posix()}])
    job.snapshot_created = True
    job.recover()
    assert overlay.read_bytes() == b"written while the backup ran"
    assert [row["disk"] for row in disk_state.attention_of("vm-fail")] == ["vdb"]


def test_nothing_is_done_after_a_failure_that_came_before_the_snapshot(database, monkeypatch):
    def forbidden(*args):
        raise AssertionError("the hypervisor must not be asked")
    job = backup_job(monkeypatch, on_overlay(), uuid="vm-early")
    monkeypatch.setattr(kvm_manage_snapshot, "open_domain", forbidden)
    job.recover()
    assert disk_state.attention_of("vm-early") == []


# -- the API: who sees the machines that wait, and who clears them ----------------------------------------------------

def test_the_machines_that_wait_are_listed_and_only_an_administrator_clears_them(database):
    with Session(database) as session:
        for name, role in (("att-admin", "admin"), ("att-viewer", "viewer")):
            if password.find_user_by_name(session, name) is None:
                session.add(User(name=name, password_hash=password.hash_password("password1"), role=role))
        session.commit()
    client = TestClient(fastapi_app)

    def headers(name):
        token = client.post("/api/v1/auth/password/login", json={"username": name, "password": "password1"}).json()
        return {"Authorization": f"Bearer {token['access_token']}"}

    disk_state.set_step("vm-api", "i-api-VM", "vdb", disk_state.NEEDS_ATTENTION, "overlay in use")
    listed = client.get("/api/v1/attention", headers=headers("att-viewer")).json()
    assert [row["vm_name"] for row in listed] == ["i-api-VM"] and listed[0]["since"]

    assert client.post("/api/v1/attention/vm-api/resolve", headers=headers("att-viewer")).status_code == 403
    assert disk_state.attention_of("vm-api")
    assert client.post("/api/v1/attention/vm-api/resolve", headers=headers("att-admin")).json() == {"cleared": 1}
    assert client.get("/api/v1/attention", headers=headers("att-viewer")).json() == []
    assert client.post("/api/v1/attention/vm-api/resolve", headers=headers("att-admin")).status_code == 404
