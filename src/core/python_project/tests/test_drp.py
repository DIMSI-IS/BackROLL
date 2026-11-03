"""Needs borg and qemu-img: it runs in the backend container, and is skipped elsewhere.

CloudStack is replaced by a fake, so these tests check the disks: extraction,
merge of the backing file and copy over the volumes of the new VM.
"""

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

os.environ.setdefault("JWT_SECRET", "x" * 40)

pytestmark = pytest.mark.skipif(
    not (shutil.which("borg") and shutil.which("qemu-img") and shutil.which("qemu-io")),
    reason="borg and qemu-img are required")


def run(*arguments, cwd=None):
    return subprocess.run(arguments, cwd=cwd, check=True, capture_output=True, text=True).stdout


def check_pattern(image: Path, offset: str, pattern: str):
    """Fails if the 4 KiB at the offset do not hold the byte pattern."""
    run("qemu-io", "-r", "-c", f"read -P {pattern} {offset} 4k", str(image))


def image_info(image: Path) -> dict:
    return json.loads(run("qemu-img", "info", "--output=json", str(image)))


class FakeCloudStack:
    """Just enough of CloudStack: the volumes are files in a storage directory."""

    def __init__(self, pool_directory: Path):
        self.pool = pool_directory
        self.jobs = {}
        self.volumes = []
        self.calls = []

    def job(self, result=None):
        identifier = f"job{len(self.jobs)}"
        self.jobs[identifier] = result or {}
        return {"jobid": identifier}

    def queryAsyncJobResult(self, jobid):
        return {"jobstatus": 1, "jobresult": self.jobs[jobid]}

    def add_volume(self, name):
        path = f"volume-{len(self.volumes)}"
        # What CloudStack creates: a small disk, not related to the backup.
        run("qemu-img", "create", "-f", "qcow2", str(self.pool / path), "1M")
        volume = {"id": f"id{len(self.volumes)}", "name": name, "path": path,
                  "storageid": "storage-1", "deviceid": len(self.volumes),
                  "type": "DATADISK" if self.volumes else "ROOT"}
        self.volumes.append(volume)
        return volume

    def deployVirtualMachine(self, **parameters):
        self.calls.append(("deploy", parameters))
        self.add_volume("ROOT-1")
        return self.job({"virtualmachine": {"id": "vm-1"}})

    def createVolume(self, **parameters):
        self.calls.append(("createVolume", parameters))
        return self.job({"volume": self.add_volume(parameters["name"])})

    def attachVolume(self, **parameters):
        self.calls.append(("attachVolume", parameters))
        return self.job()

    def stopVirtualMachine(self, **parameters):
        self.calls.append(("stop", parameters))
        return self.job()

    def startVirtualMachine(self, **parameters):
        self.calls.append(("start", parameters))
        return self.job()

    def destroyVirtualMachine(self, **parameters):
        self.calls.append(("destroy", parameters))
        return self.job()

    def listVolumes(self, **parameters):
        return {"volume": self.volumes}

    def listStoragePools(self, **parameters):
        return {"storagepool": [{"id": "pool-1"}]}


@pytest.fixture()
def environment(monkeypatch):
    from app import drp
    from app.routes import connectors

    root = Path(tempfile.mkdtemp())
    storage = root / "storage"
    templates = storage / "template"
    templates.mkdir(parents=True)
    mounts = root / "mnt"
    (mounts / "pool-1").mkdir(parents=True)

    # A CloudStack disk: a small overlay on a template. The template is saved in the template folder.
    template = templates / "template-uuid"
    run("qemu-img", "create", "-f", "qcow2", str(template), "8M")
    run("qemu-io", "-c", "write -P 0xcd 1M 4k", str(template))
    overlay_directory = root / "disks"
    overlay_directory.mkdir()
    overlay = overlay_directory / "overlay.qcow2"
    run("qemu-img", "create", "-f", "qcow2", "-b", str(template), "-F", "qcow2", str(overlay))
    run("qemu-io", "-c", "write -P 0xab 0 4k", str(overlay))
    # As on the hypervisor: the backing file is on the primary storage of CloudStack, not here.
    run("qemu-img", "rebase", "-u", "-F", "qcow2", "-b", "/mnt/original/template-uuid", str(overlay))
    # A data disk without a backing file.
    data = overlay_directory / "data.qcow2"
    run("qemu-img", "create", "-f", "qcow2", str(data), "4M")
    run("qemu-io", "-c", "write -P 0xee 0 4k", str(data))

    repository = storage / "i-1-VM"
    run("borg", "init", "--encryption", "none", "--make-parent-dirs", str(repository))
    run("borg", "create", f"{repository}::ROOT-1_overlay_1", "overlay.qcow2", cwd=str(overlay_directory))
    run("borg", "create", f"{repository}::DATA-2_data_1", "data.qcow2", cwd=str(overlay_directory))

    fake = FakeCloudStack(mounts / "pool-1")
    monkeypatch.setattr(drp, "MOUNT_ROOT", str(mounts))
    monkeypatch.setattr(drp.endpoint, "cloudstack_connector", lambda connector: fake)
    monkeypatch.setattr(connectors, "filter_connector_by_id", lambda identifier: object())
    monkeypatch.setattr(drp, "report", lambda task, step: None)

    yield drp, fake, storage, mounts
    shutil.rmtree(root, ignore_errors=True)


def request(storage, disks):
    return {
        "storage_path": str(storage), "repository": "i-1-VM", "disks": disks,
        "connector_id": "00000000-0000-0000-0000-000000000000", "name": "restored-vm",
        "zone_id": "zone", "service_offering_id": "offering", "template_id": "template",
        "network_id": "network", "ip_address": "10.0.0.5",
        "data_disk_offering_id": "custom", "start_after": True,
    }


def test_repositories_are_listed(environment):
    drp, _, storage, _ = environment
    assert drp.list_repositories(str(storage)) == ["i-1-VM"]


def test_root_disk_is_restored_standalone(environment):
    drp, fake, storage, mounts = environment

    result = drp.restore_to_new_cloudstack_vm.run(request(storage, ["ROOT-1_overlay_1"]))

    assert result["vm_id"] == "vm-1" and result["started"] is True
    restored = mounts / "pool-1" / "volume-0"
    info = image_info(restored)
    assert info["format"] == "qcow2"
    # The backing file is merged: the disk does not depend on anything.
    assert "backing-filename" not in info
    check_pattern(restored, "0", "0xab")
    check_pattern(restored, "1M", "0xcd")

    deploy = dict(fake.calls)["deploy"]
    assert deploy["rootdisksize"] == 1
    assert deploy["iptonetworklist"] == [{"networkid": "network", "ip": "10.0.0.5"}]
    assert [name for name, _ in fake.calls][-2:] == ["stop", "start"]
    # The temporary files are removed.
    assert not (storage / "restore" / ".drp").exists() or not any((storage / "restore" / ".drp").iterdir())


def test_data_disks_are_restored_to_new_volumes(environment):
    drp, fake, storage, mounts = environment

    result = drp.restore_to_new_cloudstack_vm.run(
        request(storage, ["ROOT-1_overlay_1", "DATA-2_data_1"]))

    assert len(result["volumes"]) == 2
    check_pattern(mounts / "pool-1" / "volume-1", "0", "0xee")
    assert dict(fake.calls)["createVolume"]["diskofferingid"] == "custom"


def test_volume_outside_the_storage_is_refused(environment):
    drp, fake, storage, mounts = environment
    from app.cloudstack.provisioning import CloudStackError
    with pytest.raises(CloudStackError):
        drp.get_volume_file("pool-1", {"name": "evil", "path": "../../etc/passwd"})
    with pytest.raises(CloudStackError):
        drp.get_volume_file("not-mounted", {"name": "x", "path": "x"})


def test_failure_keeps_the_new_vm_and_says_so(environment, monkeypatch):
    drp, fake, storage, mounts = environment

    def broken(*arguments, **keywords):
        raise RuntimeError("disk full")
    monkeypatch.setattr(drp, "replace_volume", broken)

    with pytest.raises(RuntimeError, match="restored-vm.*vm-1.*kept"):
        drp.restore_to_new_cloudstack_vm.run(request(storage, ["ROOT-1_overlay_1"]))


def test_vm_is_created_for_an_account_of_another_domain(environment):
    drp, fake, storage, mounts = environment
    domain = "11111111-2222-3333-4444-555555555555"

    drp.restore_to_new_cloudstack_vm.run({
        **request(storage, ["ROOT-1_overlay_1", "DATA-2_data_1"]),
        "domain_id": domain, "account": "portugal-admin"})

    deploy = dict(fake.calls)["deploy"]
    assert deploy["domainid"] == domain and deploy["account"] == "portugal-admin"
    # The data disks belong to the same account, or they could not be attached.
    volume = dict(fake.calls)["createVolume"]
    assert volume["domainid"] == domain and volume["account"] == "portugal-admin"


def test_without_a_domain_the_vm_belongs_to_the_connector_account(environment):
    drp, fake, storage, mounts = environment

    drp.restore_to_new_cloudstack_vm.run(request(storage, ["ROOT-1_overlay_1"]))

    deploy = dict(fake.calls)["deploy"]
    assert "domainid" not in deploy and "account" not in deploy


@pytest.fixture()
def history(monkeypatch):
    """The history in a memory database: the tests must not write in the real one."""
    import sqlalchemy
    from sqlalchemy.pool import StaticPool
    from sqlmodel import SQLModel
    from app import drp_history
    from app.database import DrpRun

    engine = sqlalchemy.create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine, tables=[DrpRun.__table__])
    monkeypatch.setattr(drp_history, "get_engine", lambda: engine)
    return drp_history


def history_request(storage, disks):
    return {**request(storage, disks),
            "connector_id": "00000000-0000-0000-0000-000000000001", "repository": "i-1-VM"}


def new_run(history, storage, disks=("ROOT-1_overlay_1",)):
    run_id = history.create({"id": "00000000-0000-0000-0000-0000000000aa", "username": "alice"},
                            history_request(storage, list(disks)), "Cloudstack")
    return run_id


def test_a_run_is_recorded_when_it_starts(environment, history):
    _, _, storage, _ = environment

    run_id = new_run(history, storage)

    run = history.get_run(run_id)
    assert (run["status"], run["username"], run["connector_name"], run["vm_name"]) == \
        ("queued", "alice", "Cloudstack", "restored-vm")
    assert run["disks"] == ["ROOT-1_overlay_1"] and run["finished_at"] is None


def test_a_successful_restore_is_recorded_with_its_steps(environment, history):
    drp, _, storage, _ = environment
    run_id = new_run(history, storage)

    drp.restore_to_new_cloudstack_vm.run({**history_request(storage, ["ROOT-1_overlay_1"]), "run_id": run_id})

    run = history.get_run(run_id)
    assert run["status"] == "success" and run["vm_id"] == "vm-1" and run["error"] is None
    assert run["finished_at"] is not None
    assert "Extracting the disk 1/1" in run["log"] and "Starting the restored virtual machine" in run["log"]
    assert run["step"] == "Starting the restored virtual machine"


def test_a_failed_restore_is_recorded_with_its_error(environment, history, monkeypatch):
    drp, _, storage, _ = environment
    run_id = new_run(history, storage)
    monkeypatch.setattr(drp, "replace_volume", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("disk full")))

    with pytest.raises(RuntimeError):
        drp.restore_to_new_cloudstack_vm.run({**history_request(storage, ["ROOT-1_overlay_1"]), "run_id": run_id})

    run = history.get_run(run_id)
    assert run["status"] == "failed" and "disk full" in run["error"]
    # The VM that was created is still known, to be found and cleaned.
    assert run["vm_id"] == "vm-1" and run["finished_at"] is not None


def test_runs_are_listed_from_the_newest_and_filtered(environment, history):
    _, _, storage, _ = environment
    first, second = new_run(history, storage), new_run(history, storage)
    history.finish(first, "failed", error="boom")

    everything = history.list_runs(10, 0)
    assert everything["total"] == 2 and [r["id"] for r in everything["items"]] == [second, first]
    assert [r["id"] for r in history.list_runs(10, 0, "failed")["items"]] == [first]
    assert history.list_runs(1, 1)["items"][0]["id"] == first


def test_an_old_unfinished_run_is_marked_as_interrupted(environment, history):
    from datetime import timedelta
    _, _, storage, _ = environment
    old, recent = new_run(history, storage), new_run(history, storage)
    history.update_run(old, status="running", created_at=history.now() - timedelta(hours=13))
    history.update_run(recent, status="running")

    assert history.mark_interrupted() == 1

    assert history.get_run(old)["status"] == "failed" and "Interrupted" in history.get_run(old)["error"]
    assert history.get_run(recent)["status"] == "running"


def test_the_log_is_bounded(environment, history):
    _, _, storage, _ = environment
    run_id = new_run(history, storage)
    for index in range(600):
        history.add_step(run_id, f"step number {index} " + "x" * 20)

    log = history.get_run(run_id)["log"]
    assert len(log) <= history.MAX_LOG_LENGTH and "step number 599" in log


def fail_at_the_copy(drp, monkeypatch):
    monkeypatch.setattr(drp, "replace_volume", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("disk full")))


def test_the_new_vm_is_deleted_when_asked_and_the_restore_fails(environment, monkeypatch):
    drp, fake, storage, mounts = environment
    fail_at_the_copy(drp, monkeypatch)

    with pytest.raises(RuntimeError, match="was deleted"):
        drp.restore_to_new_cloudstack_vm.run(
            {**request(storage, ["ROOT-1_overlay_1", "DATA-2_data_1"]), "cleanup_on_failure": True})

    destroy = dict(fake.calls)["destroy"]
    assert destroy["id"] == "vm-1" and destroy["expunge"] is True
    # The data disks are deleted too, the root volume goes with the machine.
    assert destroy["volumeids"] == fake.volumes[1]["id"]


def test_the_new_vm_is_kept_by_default(environment, monkeypatch):
    drp, fake, storage, mounts = environment
    fail_at_the_copy(drp, monkeypatch)

    with pytest.raises(RuntimeError, match="kept"):
        drp.restore_to_new_cloudstack_vm.run(request(storage, ["ROOT-1_overlay_1"]))

    assert "destroy" not in dict(fake.calls)


def test_nothing_is_deleted_when_the_vm_was_never_created(environment, monkeypatch):
    drp, fake, storage, mounts = environment
    monkeypatch.setattr(drp.provisioning, "deploy_vm", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("no host")))

    with pytest.raises(RuntimeError, match="no host"):
        drp.restore_to_new_cloudstack_vm.run({**request(storage, ["ROOT-1_overlay_1"]), "cleanup_on_failure": True})

    assert "destroy" not in dict(fake.calls)


def test_a_failed_deletion_is_reported(environment, monkeypatch):
    drp, fake, storage, mounts = environment
    fail_at_the_copy(drp, monkeypatch)
    monkeypatch.setattr(drp.provisioning, "destroy_vm", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("busy")))

    with pytest.raises(RuntimeError, match="could not be deleted: busy"):
        drp.restore_to_new_cloudstack_vm.run({**request(storage, ["ROOT-1_overlay_1"]), "cleanup_on_failure": True})


# -- the hook (Slack) told when the restore ends ---------------------------------------------------------------------

def test_the_hook_is_told_when_a_restore_succeeds(environment, monkeypatch):
    drp, fake, storage, mounts = environment
    posted = []
    monkeypatch.setattr(drp.notifier, "send", lambda hook_id, text, blocks=None: posted.append((hook_id, text)))
    drp.restore_to_new_cloudstack_vm.run({**request(storage, ["ROOT-1_overlay_1"]), "hook_id": "hook-1"})
    [(hook_id, text)] = posted
    assert hook_id == "hook-1"
    assert "finished" in text and "restored-vm" in text and "i-1-VM" in text and "<!channel>" not in text


def test_the_hook_is_told_and_the_channel_alerted_when_a_restore_fails(environment, monkeypatch):
    drp, fake, storage, mounts = environment
    posted = []
    monkeypatch.setattr(drp.notifier, "send", lambda hook_id, text, blocks=None: posted.append((hook_id, text)))

    def broken(*arguments, **keywords):
        raise RuntimeError("disk full")
    monkeypatch.setattr(drp, "replace_volume", broken)
    with pytest.raises(RuntimeError, match="disk full"):
        drp.restore_to_new_cloudstack_vm.run({**request(storage, ["ROOT-1_overlay_1"]), "hook_id": "hook-1"})
    [(hook_id, text)] = posted
    assert hook_id == "hook-1" and "<!channel>" in text and "failed" in text and "disk full" in text


def test_a_restore_without_hook_tells_nobody(environment, monkeypatch):
    drp, fake, storage, mounts = environment
    posted = []
    monkeypatch.setattr(drp.notifier, "send", lambda hook_id, text, blocks=None: posted.append(hook_id))
    drp.restore_to_new_cloudstack_vm.run(request(storage, ["ROOT-1_overlay_1"]))
    # The notifier is called with no hook, and does nothing.
    assert posted == [None]


# -- the free space of a restore: only what is written is counted --------------------------------------------------------

def test_a_standalone_disk_is_checked_once_and_a_disk_with_a_backing_file_a_second_time_for_its_conversion(environment, monkeypatch, tmp_path):
    drp, fake, storage, mounts = environment
    asked = []
    monkeypatch.setattr(drp.file_browser, "check_free_space",
                        lambda directory, needed, copies=1: asked.append((needed, copies)))

    # A data disk without backing file: the extraction is checked, nothing else is written.
    drp.prepare_disk(str(storage), "i-1-VM", "DATA-2_data_1", tmp_path / "data")
    assert len(asked) == 1 and asked[0][1] == 1

    # A CloudStack disk on its template: after the extraction, the conversion is checked with the data of the chain.
    asked.clear()
    drp.prepare_disk(str(storage), "i-1-VM", "ROOT-1_overlay_1", tmp_path / "root")
    assert len(asked) == 2 and asked[1][1] == 1
    assert asked[1][0] > 0


def test_a_restore_is_refused_before_anything_is_written_when_the_disk_would_be_full(environment, monkeypatch, tmp_path):
    drp, fake, storage, mounts = environment
    from app import file_browser
    monkeypatch.setattr(file_browser, "archive_size", lambda *arguments: 12 * 1024 ** 3)
    free = type("Usage", (), {"total": 0, "used": 0, "free": 5 * 1024 ** 3})()
    monkeypatch.setattr(shutil, "disk_usage", lambda path: free)
    with pytest.raises(file_browser.NotEnoughSpace, match="Not enough free space"):
        drp.prepare_disk(str(storage), "i-1-VM", "ROOT-1_overlay_1", tmp_path / "root")
    assert not (tmp_path / "root").exists()


def test_a_failure_to_record_the_end_does_not_delete_the_machine_that_was_restored(environment, history, monkeypatch):
    """The restore is done and the machine runs: the record of its end is only a record. A database that fails at
    that moment used to send the task to the cleaning, which deleted the machine that had just been restored."""
    drp, fake, storage, mounts = environment
    run_id = new_run(history, storage)
    real_finish = history.finish
    calls = []

    def finish_fails_once(*arguments, **keywords):
        calls.append(arguments)
        if len(calls) == 1:
            raise RuntimeError("database down")
        return real_finish(*arguments, **keywords)
    monkeypatch.setattr(drp.drp_history, "finish", finish_fails_once)

    result = drp.restore_to_new_cloudstack_vm.run(
        {**history_request(storage, ["ROOT-1_overlay_1"]), "run_id": run_id, "cleanup_on_failure": True})

    assert result["vm_id"] == "vm-1"
    assert "destroy" not in dict(fake.calls)


def test_a_failure_to_record_a_step_does_not_stop_the_restore(environment, history, monkeypatch):
    drp, fake, storage, mounts = environment
    run_id = new_run(history, storage)

    def broken(*arguments, **keywords):
        raise RuntimeError("database down")
    monkeypatch.setattr(drp.drp_history, "add_step", broken)

    result = drp.restore_to_new_cloudstack_vm.run(
        {**history_request(storage, ["ROOT-1_overlay_1"]), "run_id": run_id, "cleanup_on_failure": True})

    assert result["vm_id"] == "vm-1" and "destroy" not in dict(fake.calls)
