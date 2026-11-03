"""A refusal of the API is told to the user with its reason, with the right status: not an error 500 without a message.

These cases were found by the acceptance tests of the beta: the protections worked, but the person saw
"Request failed with status code 500".
"""

import os
import tempfile
from types import SimpleNamespace
from uuid import UUID

import pytest

os.environ.setdefault("SQLITE_DIRECTORY", tempfile.mkdtemp())
os.environ.setdefault("JWT_SECRET", "x" * 40)

pytest.importorskip("app.routes.backup_policy")

from fastapi.testclient import TestClient  # noqa: E402
from sqlmodel import Session, SQLModel  # noqa: E402

from app import auth, database, vault  # noqa: E402
from app.database import Hosts, Pools, Storage  # noqa: E402
from app.initialized import fastapi_app  # noqa: E402
from app.routes import backup_policy, connectors, external_hooks  # noqa: E402


@pytest.fixture
def client():
    SQLModel.metadata.create_all(database.init_db_connection())
    fastapi_app.dependency_overrides[auth.require_editor] = lambda: {}
    yield TestClient(fastapi_app, raise_server_exceptions=False)
    fastapi_app.dependency_overrides.clear()


def new_storage(name="storage", path="/mnt/backups"):
    with Session(database.init_db_connection()) as session:
        row = Storage(name=name, path=path)
        session.add(row)
        session.commit()
        session.refresh(row)
        return str(row.id)


def policy_body(storage_id, name="nightly", **more):
    body = {"name": name, "schedule": "0 22 * * *", "retention": {"day": 3, "week": 1, "month": 1, "year": 0},
            "storage": storage_id}
    body.update(more)
    return body


# -- the policies -----------------------------------------------------------------------------------------------------

def test_a_policy_without_description_is_created_with_an_empty_one(client):
    answer = client.post("/api/v1/backup_policies", json=policy_body(new_storage(), name="no-description"))
    assert answer.status_code == 201, answer.text
    assert answer.json()["description"] == ""


@pytest.mark.parametrize("retention", [{"days": 3}, {"day": -1}, {"day": "many"}])
def test_a_retention_with_an_unknown_key_or_a_wrong_number_is_refused_with_422(client, retention):
    answer = client.post("/api/v1/backup_policies", json=policy_body(new_storage(), name="bad-retention", retention=retention))
    assert answer.status_code == 422
    # The answer names the field.
    assert "retention" in answer.text


def test_a_missing_retention_key_is_zero(client):
    answer = client.post("/api/v1/backup_policies",
                         json=policy_body(new_storage(), name="partial-retention", retention={"day": 7}))
    assert answer.status_code == 201, answer.text
    assert answer.json()["retention_day"] == 7 and answer.json()["retention_week"] == 0


def test_two_policies_cannot_have_the_same_name_whatever_the_case(client):
    storage_id = new_storage()
    assert client.post("/api/v1/backup_policies", json=policy_body(storage_id, name="Same Name")).status_code == 201
    answer = client.post("/api/v1/backup_policies", json=policy_body(storage_id, name="same name"))
    assert answer.status_code == 409
    assert "already exists" in answer.json()["detail"]


def test_a_policy_can_be_renamed_to_its_own_name_but_not_to_the_name_of_another(client):
    storage_id = new_storage()
    first = client.post("/api/v1/backup_policies", json=policy_body(storage_id, name="first")).json()
    client.post("/api/v1/backup_policies", json=policy_body(storage_id, name="second"))
    assert client.patch(f"/api/v1/backup_policies/{first['id']}", json={"name": "first"}).status_code == 200
    assert client.patch(f"/api/v1/backup_policies/{first['id']}", json={"name": "SECOND"}).status_code == 409


def test_a_policy_cannot_be_enabled_on_a_pool_without_hypervisor_and_the_reason_is_told(client):
    storage_id = new_storage()
    policy = client.post("/api/v1/backup_policies", json=policy_body(storage_id, name="for-an-empty-pool")).json()
    with Session(database.init_db_connection()) as session:
        session.add(Pools(name="empty-pool", policy_id=UUID(policy["id"])))
        session.commit()

    answer = client.patch(f"/api/v1/backup_policies/{policy['id']}", json={"enabled": True})

    assert answer.status_code == 403
    assert "empty pool" in answer.json()["detail"]


def test_a_policy_that_does_not_exist_is_a_404(client):
    answer = client.patch("/api/v1/backup_policies/00000000-0000-0000-0000-000000000000", json={"description": "x"})
    assert answer.status_code == 404


# -- the connectors ---------------------------------------------------------------------------------------------------

def test_a_connector_used_by_a_pool_is_refused_with_409_and_the_name_of_the_pool(client):
    used = connectors.api_create_connector.run("in-use", "http://cs/client/api", "key", "secret")
    with Session(database.init_db_connection()) as session:
        session.add(Pools(name="pool-of-the-connector", connector_id=UUID(used["id"])))
        session.commit()

    answer = client.delete(f"/api/v1/connectors/{used['id']}")

    assert answer.status_code == 409
    assert "pool-of-the-connector" in answer.json()["detail"]


def test_a_connector_that_does_not_exist_is_a_404(client):
    unknown = "00000000-0000-0000-0000-000000000000"
    assert client.delete(f"/api/v1/connectors/{unknown}").status_code == 404
    assert client.patch(f"/api/v1/connectors/{unknown}", json={"name": "x", "url": "http://x"}).status_code == 404


# -- the storages -----------------------------------------------------------------------------------------------------

def test_two_storages_cannot_have_the_same_name_or_the_same_path(client):
    assert client.post("/api/v1/storage", json={"name": "backups-a", "path": "/mnt/a"}).status_code == 201
    same_name = client.post("/api/v1/storage", json={"name": "Backups-A", "path": "/mnt/other"})
    same_path = client.post("/api/v1/storage", json={"name": "other", "path": "/mnt/a/"})
    assert same_name.status_code == 409 and "already exists" in same_name.json()["detail"]
    assert same_path.status_code == 409 and "backups-a" in same_path.json()["detail"]


def test_a_storage_can_be_saved_again_under_its_own_name_and_path(client):
    created = client.post("/api/v1/storage", json={"name": "backups-b", "path": "/mnt/b"}).json()
    answer = client.patch(f"/api/v1/storage/{created['id']}", json={"name": "backups-b", "path": "/mnt/b"})
    assert answer.status_code == 200, answer.text


# -- the hooks and the secrets ----------------------------------------------------------------------------------------

def test_a_hook_used_by_a_policy_is_refused_with_409_and_the_name_of_the_policy(client):
    hook = external_hooks.api_create_external_hook.run("slack", "https://hooks.slack.test/services/abc")
    client.post("/api/v1/backup_policies", json=policy_body(new_storage(), name="with-hook", externalhook=hook["id"]))

    answer = client.delete(f"/api/v1/externalhooks/{hook['id']}")

    assert answer.status_code == 409
    assert "with-hook" in answer.json()["detail"]


def test_a_secret_that_cannot_be_read_any_more_is_told_with_409_and_what_to_do(client, monkeypatch):
    # The key changed: the test of a hook decrypts the address, which fails.
    def unreadable(hook_id):
        raise vault.SecretError("A stored secret could not be decrypted: the key changed. Type it again in the settings.")
    monkeypatch.setattr(external_hooks.notification_sender, "test", unreadable)

    answer = client.get("/api/v1/externalhooks/00000000-0000-0000-0000-000000000000/test")

    assert answer.status_code == 409
    assert "Type it again" in answer.json()["detail"]


# -- the machines, the messages of the backups ------------------------------------------------------------------------

def test_a_backup_of_a_machine_that_does_not_exist_fails_with_a_message_that_says_so():
    virtual_machine = pytest.importorskip("app.routes.virtual_machine")
    machines = [{"uuid": "vm-1", "name": "web"}]
    assert virtual_machine.filter_virtual_machine_list.run(machines, "vm-1")["name"] == "web"
    # The status of the task answers 404 when the text says "not found".
    with pytest.raises(ValueError, match="not found"):
        virtual_machine.filter_virtual_machine_list.run(machines, "vm-unknown")


def test_a_machine_without_the_guest_agent_gets_a_message_that_says_what_to_install(monkeypatch):
    pytest.importorskip("libvirt")
    from app.kvm import kvm_manage_snapshot

    class Domain:
        def snapshotCreateXML(self, xml, flags):
            raise Exception("argument unsupported: QEMU guest agent is not configured")

    class Connection:
        def lookupByName(self, name):
            return Domain()

        def close(self):
            pass

    monkeypatch.setattr(kvm_manage_snapshot.kvm_connection, "kvm_connection", lambda hypervisor: Connection())

    with pytest.raises(ValueError, match="qemu-guest-agent"):
        kvm_manage_snapshot.createSnapshot({"name": "web-01"}, {}, "<xml/>")


def test_the_message_of_the_end_of_a_task_gives_the_state_it_ended_with_not_the_one_the_monitor_still_reports(monkeypatch):
    from app.hooks import notification_sender
    told = []
    client = SimpleNamespace(on_task_failure=lambda task, message: told.append(task["state"]),
                             on_task_success=lambda task, message: told.append(task["state"]))
    # The monitor was a step behind: it still says STARTED.
    monkeypatch.setattr(notification_sender, "__from_task_id", lambda task_id: ({"state": "STARTED"}, client))
    monkeypatch.setattr(notification_sender.time, "sleep", lambda seconds: None)
    # Flower never says the end: the message goes out anyway, with the state of the signal.
    monkeypatch.setattr(notification_sender.task_helper, "get_task_info", lambda task_id: b"{}")

    notification_sender.on_task_failure("task", "ended")
    notification_sender.on_task_success("task", "ended")

    assert told == ["FAILURE", "SUCCESS"]


def test_a_repository_that_stays_locked_is_told_as_such(monkeypatch):
    borg_core = pytest.importorskip("app.borg.borg_core")

    def locked(command):
        raise RuntimeError("Failed to create/acquire the lock /mnt/backups/web-01/lock.exclusive (timeout).")
    monkeypatch.setattr(borg_core.shell, "subprocess_run", locked)
    job = borg_core.borg_backup.__new__(borg_core.borg_backup)
    job.info = {"name": "web-01", "borg_repository": "/mnt/backups"}

    with pytest.raises(ValueError, match="locked by another operation"):
        job.check_repository_lock()
