"""The messages sent to an external hook (Slack) outside the end of a backup task: the end of a disaster
recovery, a disk that needs attention. A fake Slack records what would be posted."""

import os

import pytest
from sqlmodel import Session, SQLModel

pytest.importorskip("libvirt")

from app import disk_state, notifier  # noqa: E402
from app.borg import borg_core  # noqa: E402
from app.database import ExternalHooks, init_db_connection  # noqa: E402

SECRET = "https://hooks.slack.com/services/T0AAAAAAA/B0BBBBBBB/xyz123SECRETvalue9"


class FakeWebhook:
    sent = []
    fail_with = None

    def __init__(self, url, *args, **kwargs):
        self.url = url

    def send(self, **message):
        if FakeWebhook.fail_with:
            raise FakeWebhook.fail_with
        FakeWebhook.sent.append({"url": self.url, **message})


@pytest.fixture(autouse=True)
def fake_slack(monkeypatch):
    FakeWebhook.sent, FakeWebhook.fail_with = [], None
    monkeypatch.setattr("slack_sdk.webhook.WebhookClient", FakeWebhook)
    monkeypatch.setenv("FRONT_URL", "https://backroll.example/")


@pytest.fixture
def hook():
    engine = init_db_connection()
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        row = ExternalHooks(name="notifications-hook", value=SECRET)
        session.add(row)
        session.commit()
        session.refresh(row)
    return row


def test_a_message_goes_to_the_address_of_the_hook(hook):
    notifier.send(hook.id, "hello")
    notifier.send(str(hook.id), "again")
    assert [(m["url"], m["text"]) for m in FakeWebhook.sent] == [(SECRET, "hello"), (SECRET, "again")]


def test_no_hook_an_unknown_hook_or_a_slack_that_is_down_never_raise(hook):
    notifier.send(None, "nobody")
    notifier.send("00000000-0000-0000-0000-000000000000", "unknown")
    notifier.send("not a uuid", "broken id")
    FakeWebhook.fail_with = RuntimeError("Slack is down")
    notifier.send(hook.id, "no answer")
    assert FakeWebhook.sent == []


def test_the_link_to_the_interface_is_built_from_its_address(monkeypatch):
    assert notifier.front_url("admin/dashboard") == "https://backroll.example/admin/dashboard"
    monkeypatch.delenv("FRONT_URL")
    assert notifier.front_url("admin/dashboard") == ""


def test_the_message_of_a_disk_that_needs_attention_says_what_to_do():
    text = notifier.attention_message("i-535-18737-VM", "vdb", "the machine already writes in an overlay")
    assert "<!channel>" in text and "i-535-18737-VM" in text and "`vdb`" in text and "overlay" in text
    assert "https://backroll.example/admin/dashboard" in text


def test_the_messages_of_a_disaster_recovery():
    request = {"name": "restored-vm", "repository": "i-1-VM", "disks": ["a", "b"], "account": "drp-test"}
    done = notifier.drp_finished_message(request, "vm-42")
    assert "restored-vm" in done and "i-1-VM" in done and "2 disk(s)" in done and "drp-test" in done and "vm-42" in done
    assert "<!channel>" not in done
    failed = notifier.drp_failed_message(request, "disk full")
    assert "<!channel>" in failed and "disk full" in failed and "restored-vm" in failed


def test_the_hook_of_the_policy_of_a_machine_is_told(hook, monkeypatch):
    from app import policy_lookup
    monkeypatch.setattr(policy_lookup, "policy_of", lambda vm: type("Policy", (), {"externalhook": hook.id})())
    notifier.send_to_policy_hook({"name": "i-1-VM"}, "from the policy")
    assert [m["text"] for m in FakeWebhook.sent] == ["from the policy"]
    # A machine without a policy, or a policy without a hook, tells nobody and breaks nothing.
    monkeypatch.setattr(policy_lookup, "policy_of", lambda vm: type("Policy", (), {"externalhook": None})())
    notifier.send_to_policy_hook({"name": "i-1-VM"}, "nobody")
    monkeypatch.setattr(policy_lookup, "policy_of", lambda vm: (_ for _ in ()).throw(KeyError("pool_id")))
    notifier.send_to_policy_hook({"name": "i-1-VM"}, "no policy")
    assert len(FakeWebhook.sent) == 1


def test_a_disk_that_needs_attention_is_told_once_not_at_every_attempt(monkeypatch):
    engine = init_db_connection()
    SQLModel.metadata.create_all(engine)
    told = []
    monkeypatch.setattr(notifier, "send_to_policy_hook", lambda vm, text, blocks=None: told.append(text))
    job = borg_core.borg_backup({"name": "i-once-VM", "uuid": "vm-once"}, None)
    job.vm_name = "i-once-VM"
    job.attention("vdb", "the machine already writes in an overlay")
    job.attention("vdb", "the machine already writes in an overlay")
    assert len(told) == 1 and "i-once-VM" in told[0]
    # Once cleared, a new problem is told again.
    disk_state.clear("vm-once")
    job.attention("vdb", "a new problem")
    assert len(told) == 2 and "a new problem" in told[1]
    # Another disk of the same machine is another problem.
    job.attention("vda", "another disk")
    assert len(told) == 3


# -- the route of the disaster recovery ------------------------------------------------------------------------------

def test_the_route_of_the_disaster_recovery_checks_the_hook_and_passes_it_on(hook, monkeypatch):
    from fastapi.testclient import TestClient
    from app import drp_history
    from app.auth import password
    from app.database import User, migrate_user_table
    from app.initialized import fastapi_app
    from app.routes import drp as drp_routes
    from app.routes import task  # noqa: F401  (the route that gives the state of a task)
    from app.routes.auth import password as password_routes  # noqa: F401

    engine = init_db_connection()
    migrate_user_table(engine)
    with Session(engine) as session:
        if password.find_user_by_name(session, "notif-admin") is None:
            session.add(User(name="notif-admin", password_hash=password.hash_password("password1"), role="admin"))
            session.commit()
    client = TestClient(fastapi_app)
    token = client.post("/api/v1/auth/password/login", json={"username": "notif-admin", "password": "password1"}).json()
    headers = {"Authorization": f"Bearer {token['access_token']}"}

    started = []
    monkeypatch.setattr(drp_routes, "get_storage_path", lambda storage_id: "/tmp/storage")
    monkeypatch.setattr(drp_routes, "get_connector", lambda connector_id: type("Connector", (), {"name": "lab"})())
    monkeypatch.setattr(drp_routes, "list_archives", lambda path, repository: [{"name": "ROOT-1_overlay_1"}])
    monkeypatch.setattr(drp_history, "create", lambda identity, request, name: "run-1")
    monkeypatch.setattr(drp_history, "set_task", lambda run_id, task_id: None)
    monkeypatch.setattr(drp_routes.drp.restore_to_new_cloudstack_vm, "delay",
                        lambda request: started.append(request) or type("Task", (), {"id": "task-1"})())

    identifier = "00000000-0000-0000-0000-000000000001"
    body = {"storage_id": identifier, "repository": "i-1-VM", "disks": ["ROOT-1_overlay_1"], "connector_id": identifier,
            "name": "restored-vm", "zone_id": identifier, "service_offering_id": identifier, "template_id": identifier}

    unknown = client.post("/api/v1/drp/restore", headers=headers, json={**body, "hook_id": identifier})
    assert unknown.status_code == 422 and "hook" in unknown.text and started == []

    known = client.post("/api/v1/drp/restore", headers=headers, json={**body, "hook_id": str(hook.id)})
    assert known.status_code == 202 and started[-1]["hook_id"] == str(hook.id)

    none = client.post("/api/v1/drp/restore", headers=headers, json=body)
    assert none.status_code == 202 and "hook_id" not in started[-1]


# -- the cleaning of the backups ---------------------------------------------------------------------------------------

@pytest.fixture
def cleaning(monkeypatch):
    """A storage whose cleaning tells the hook "hook-1": what is posted is recorded, nothing is deleted."""
    from uuid import uuid4
    from app import cleanup
    from app.routes import cleanup as routes

    storage = type("Storage", (), {"id": uuid4(), "name": "BACKUP_STORAGE", "path": "/tmp/none"})()
    posted, finished = [], []
    monkeypatch.setattr(cleanup, "get_storage", lambda storage_id: storage)
    monkeypatch.setattr(cleanup, "get_settings", lambda storage_id: type("Settings", (), {"keep_days": 30, "hook_id": "hook-1"})())
    monkeypatch.setattr(cleanup, "has_running_run", lambda storage_id: False)
    monkeypatch.setattr(cleanup, "create_run", lambda *args: "00000000-0000-0000-0000-000000000009")
    monkeypatch.setattr(cleanup, "finish_run", lambda run_id, status, summary, log: finished.append(status))
    monkeypatch.setattr(cleanup, "notify", lambda hook_id, text, blocks=None: posted.append((hook_id, text, blocks)))
    return routes, storage, posted, finished


def test_a_cleaning_tells_the_hook_when_it_starts_and_ends(cleaning, monkeypatch):
    routes, storage, posted, finished = cleaning
    from app import cleanup
    monkeypatch.setattr(cleanup, "prune_storage", lambda path, days, log: {
        "repositories": 3, "archives_deleted": 12, "freed_bytes": 5 * 1024 ** 3, "errors": 0})
    routes.cleanup_storage.run(str(storage.id), trigger="manual")
    assert [call[0] for call in posted] == ["hook-1", "hook-1"]
    assert "started" in posted[0][1] and "BACKUP_STORAGE" in posted[0][1]
    assert "finished" in posted[1][1] and "<!channel>" not in posted[1][1]
    assert finished == ["success"]


def test_a_failed_cleaning_alerts_the_channel(cleaning, monkeypatch):
    routes, storage, posted, finished = cleaning
    from app import cleanup

    def broken(path, days, log):
        raise RuntimeError("the storage is not mounted")
    monkeypatch.setattr(cleanup, "prune_storage", broken)
    routes.cleanup_storage.run(str(storage.id), trigger="scheduled")
    assert "<!channel>" in posted[-1][1] and "FAILED" in posted[-1][1]
    assert finished == ["failed"]


def test_the_deletion_of_the_backups_of_deleted_machines_is_told_too(cleaning, monkeypatch):
    routes, storage, posted, finished = cleaning
    from app import cleanup
    monkeypatch.setattr(routes, "machine_names", lambda: ({"web-01"}, []))
    monkeypatch.setattr(cleanup, "delete_repository",
                        lambda path, name, log: {"deleted": True, "archives": 31, "size_bytes": 12 * 1024 ** 3})
    routes.delete_orphan_backups.run(str(storage.id), ["i-2-100-VM", "web-01"], "00000000-0000-0000-0000-000000000009")
    assert "Deletion of the backups of deleted machines started" in posted[0][1]
    assert "finished" in posted[-1][1] and "<!channel>" not in posted[-1][1]
    assert finished == ["success"]


def test_a_deletion_refused_because_the_machines_can_not_be_listed_alerts_the_channel(cleaning, monkeypatch):
    routes, storage, posted, finished = cleaning
    from app import cleanup
    monkeypatch.setattr(routes, "machine_names", lambda: (set(), ["The hypervisor kvm-1 is not reachable."]))
    deleted = []
    monkeypatch.setattr(cleanup, "delete_repository", lambda *args: deleted.append(args) or {"deleted": True, "archives": 1, "size_bytes": 1})
    routes.delete_orphan_backups.run(str(storage.id), ["i-2-100-VM"], "00000000-0000-0000-0000-000000000009")
    assert deleted == []
    assert "<!channel>" in posted[-1][1] and finished == ["failed"]


def test_the_deletion_of_the_chosen_backups_is_told_and_recorded(cleaning, monkeypatch):
    routes, storage, posted, finished = cleaning
    from app import cleanup
    received = []

    def fake(path, selection, days, log):
        received.append((selection, days))
        return {"repositories": 1, "archives_deleted": 2, "freed_bytes": 1024 ** 3, "errors": 0}
    monkeypatch.setattr(cleanup, "delete_selected", fake)
    routes.delete_selected_backups.run(str(storage.id), {"web-01": ["vda_x_1", "vda_x_2"]},
                                       "00000000-0000-0000-0000-000000000009")
    assert received == [({"web-01": ["vda_x_1", "vda_x_2"]}, 30)]
    assert "started" in posted[0][1] and "finished" in posted[-1][1] and "<!channel>" not in posted[-1][1]
    assert finished == ["success"]


def test_a_failure_while_deleting_the_chosen_backups_alerts_the_channel_and_ends_the_run(cleaning, monkeypatch):
    routes, storage, posted, finished = cleaning
    from app import cleanup

    def broken(path, selection, days, log):
        raise RuntimeError("the storage is not mounted")
    monkeypatch.setattr(cleanup, "delete_selected", broken)
    routes.delete_selected_backups.run(str(storage.id), {"web-01": ["vda_x_1"]}, "00000000-0000-0000-0000-000000000009")
    assert "<!channel>" in posted[-1][1] and finished == ["failed"]


def test_the_simulation_uses_the_saved_number_of_days_and_deletes_nothing(cleaning, monkeypatch):
    routes, storage, posted, finished = cleaning
    from app import cleanup
    monkeypatch.setattr(cleanup, "plan_storage", lambda path, days: {"repositories": [], "archives": 0, "errors": [],
                                                                      "days_seen": days})
    result = routes.simulate_cleanup.run(str(storage.id))
    assert result["keep_days"] == 30 and result["days_seen"] == 30
    # A simulation tells nobody and records nothing.
    assert posted == [] and finished == []


# -- the look of the messages ---------------------------------------------------------------------------------------------

def titles(blocks):
    return [b["text"]["text"] for b in blocks if b["type"] == "header"]


def all_text(blocks):
    return " ".join(str(b) for b in blocks)


def test_sizes_are_shown_in_the_unit_that_fits():
    assert notifier.human_size(0) == "0 B" and notifier.human_size(512) == "512 B"
    assert notifier.human_size(5 * 1024 ** 2) == "5.0 MiB"
    assert notifier.human_size(5368709120) == "5.0 GiB"
    assert notifier.human_size(3 * 1024 ** 4) == "3.0 TiB"
    assert notifier.human_size(5000 * 1024 ** 4) == "5000.0 TiB"


def test_a_card_has_a_title_the_facts_the_detail_a_button_and_a_footer():
    blocks = notifier.card("Title", [("A", "1"), ("Empty", None), ("B", "2")], "detail", mention=True, button=("Open", "https://x"))
    assert [b["type"] for b in blocks] == ["header", "section", "section", "section", "actions", "context"]
    assert [f["text"] for f in blocks[2]["fields"]] == ["*A*\n1", "*B*\n2"]
    assert "<!channel>" in blocks[1]["text"]["text"]
    # No button without an address, no alert without a reason to alert.
    plain = notifier.card("Title", [("A", "1")], button=("Open", ""))
    assert [b["type"] for b in plain] == ["header", "section", "context"]


def test_the_disk_that_needs_attention_is_a_card_that_says_what_to_do():
    blocks = notifier.attention_blocks("i-535-18737-VM", "vdb", "the machine already writes in an overlay")
    assert titles(blocks) == [":warning: Backups stopped: i-535-18737-VM"]
    text = all_text(blocks)
    assert "<!channel>" in text and "`vdb`" in text and "virsh domblklist i-535-18737-VM" in text
    assert "https://backroll.example/admin/dashboard" in text


def test_the_cards_of_the_disaster_recovery():
    request = {"name": "restored-vm", "repository": "i-1-VM", "disks": ["a", "b"], "account": "drp-test"}
    done = notifier.drp_finished_blocks(request, "vm-42")
    assert titles(done) == [":white_check_mark: Disaster recovery restore finished"] and "<!channel>" not in all_text(done)
    assert "restored-vm" in all_text(done) and "drp-test" in all_text(done) and "vm-42" in all_text(done)
    failed = notifier.drp_failed_blocks(request, "disk full")
    assert titles(failed) == [":x: Disaster recovery restore failed"] and "<!channel>" in all_text(failed)
    assert "disk full" in all_text(failed)
    # A restore without account or id does not show empty facts.
    bare = notifier.drp_finished_blocks({"name": "x", "repository": "r", "disks": ["a"]}, None)
    assert "Account" not in all_text(bare) and "CloudStack id" not in all_text(bare)


def test_the_cards_of_the_cleaning():
    summary = {"repositories": 3, "archives_deleted": 12, "freed_bytes": 5368709120, "errors": 0}
    started = notifier.cleaning_started_blocks("BACKUP_STORAGE", "old")
    assert titles(started) == [":broom: Cleaning started"] and "Old backups" in all_text(started)
    done = notifier.cleaning_finished_blocks("BACKUP_STORAGE", "deleted", "success", summary)
    assert titles(done) == [":white_check_mark: Cleaning finished"] and "5.0 GiB" in all_text(done)
    assert "Backups of deleted machines" in all_text(done) and "<!channel>" not in all_text(done)
    failed = notifier.cleaning_finished_blocks("BACKUP_STORAGE", "old", "failed", {**summary, "errors": 2})
    assert titles(failed) == [":x: Cleaning failed"] and "<!channel>" in all_text(failed)


def test_the_cards_are_sent_with_the_plain_text_as_a_fallback(hook):
    notifier.send(hook.id, "plain text", notifier.card("Title", [("A", "1")]))
    [message] = FakeWebhook.sent
    assert message["text"] == "plain text" and message["blocks"][0]["type"] == "header"
    notifier.send(hook.id, "only text")
    assert "blocks" not in FakeWebhook.sent[-1]


def test_the_summary_of_a_cleaning_gives_a_readable_size():
    from app import cleanup
    assert "5.0 GiB freed" in cleanup.summary_text({"repositories": 3, "archives_deleted": 12, "freed_bytes": 5368709120, "errors": 0})
