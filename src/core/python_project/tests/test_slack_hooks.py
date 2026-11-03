"""Slack notifications: what is sent, to whom, and that the address of the webhook never leaves the server.

A fake Slack client records what would be posted; nothing is sent to a real channel here.
"""

import json
import os
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from slack_sdk.errors import SlackApiError
from sqlmodel import Session, SQLModel, select

pytest.importorskip("libvirt")

from app import cleanup, task_handler, vault  # noqa: E402
from app.auth import password  # noqa: E402
from app.database import ExternalHooks, User, init_db_connection, migrate_user_table  # noqa: E402
from app.hooks import notification_sender, slack  # noqa: E402
from app.initialized import fastapi_app  # noqa: E402
from app.routes import external_hooks  # noqa: E402
from app.routes.auth import password as password_routes  # noqa: E402,F401

SECRET = "https://hooks.slack.com/services/T0AAAAAAA/B0BBBBBBB/xyz123SECRETvalue9"


class FakeWebhook:
    """Stands for slack_sdk.webhook.WebhookClient: records the messages instead of posting them."""
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
    monkeypatch.setattr(slack, "WebhookClient", FakeWebhook)
    monkeypatch.setattr("slack_sdk.webhook.WebhookClient", FakeWebhook)
    # The success and failure messages wait 10 seconds so that the task is recorded first.
    monkeypatch.setattr(slack.time, "sleep", lambda seconds: None)
    monkeypatch.setenv("FRONT_URL", "https://backroll.example")


def text_of(message) -> str:
    return json.dumps(message["blocks"], ensure_ascii=False)


TASK = {"name": "Single_VM_Backup", "state": "SUCCESS", "started": 1792431000, "runtime": 125,
        "args": [{"name": "i-2-17543-VM"}]}


# -- what is posted ----------------------------------------------------------------------------------------------

def test_a_successful_backup_is_posted_without_alerting_the_channel():
    slack.SlackClient(SECRET).on_task_success(TASK, "A new single VM backup job has ended")
    [message] = FakeWebhook.sent
    assert message["url"] == SECRET
    assert "i-2-17543-VM" in text_of(message) and "has ended" in text_of(message)
    assert "<!channel>" not in text_of(message)


def test_a_failed_backup_alerts_the_channel():
    slack.SlackClient(SECRET).on_task_failure({**TASK, "state": "FAILURE"}, "A new single VM backup job has exited")
    [message] = FakeWebhook.sent
    assert "<!channel>" in text_of(message) and "i-2-17543-VM" in text_of(message)


def test_the_summary_of_a_pool_counts_and_alerts_only_when_something_failed():
    pool = SimpleNamespace(name="Production")
    received = __import__("datetime").datetime(2026, 10, 19, 21, 0)
    client = slack.SlackClient(SECRET)
    client.on_pool(pool, [{"name": "a"}, {"name": "b"}], [], received)
    client.on_pool(pool, [{"name": "a"}], [ValueError("disk missing")], received)
    quiet, loud = FakeWebhook.sent
    assert "<!channel>" not in text_of(quiet) and "<!channel>" in text_of(loud)
    assert "*2* Successful" in text_of(quiet) and "*1* Failed" in text_of(loud)
    assert "backroll.example/admin/tasks/backup?date=2026-10-19" in text_of(quiet)
    # Nothing about the machines that are not running when there are none.
    assert "Skipped" not in text_of(quiet)


def test_the_machines_that_are_not_running_are_counted_as_skipped_not_as_failures():
    pool = SimpleNamespace(name="Production")
    slack.SlackClient(SECRET).on_pool(pool, [{"name": "a"}], [], __import__("datetime").datetime(2026, 10, 19, 21, 0),
                                      [{"name": "off-1"}, {"name": "off-2"}])
    [message] = FakeWebhook.sent
    assert "*2* Skipped (not running)" in text_of(message)
    assert "*0* Failed" in text_of(message) and "<!channel>" not in text_of(message)


def test_a_slack_error_does_not_break_the_backup():
    FakeWebhook.fail_with = SlackApiError("invalid_token", {"ok": False, "error": "invalid_token"})
    slack.SlackClient(SECRET).on_task_success(TASK, "ended")  # must not raise


# -- who is told -------------------------------------------------------------------------------------------------

class Recorder:
    def __init__(self):
        self.calls = []

    def on_task_success(self, task, message):
        self.calls.append(("success", message))

    def on_task_failure(self, task, message):
        self.calls.append(("failure", message))

    def on_pool(self, pool, success_list, failure_list, received, skipped_list=None, blocked_list=None):
        self.calls.append(("pool", success_list, failure_list, skipped_list, blocked_list))


def test_the_results_of_a_pool_are_sorted_into_success_failure_and_skipped(monkeypatch):
    recorder = Recorder()
    monkeypatch.setattr(notification_sender, "__from_pool_id", lambda pool_id: (SimpleNamespace(name="P"), recorder))
    notification_sender.on_pool([
        {"status": "success", "info": {"name": "ok"}},
        {"status": "skipped", "info": {"name": "off"}},
        "ValueError: boom",
        "BackupStateError: NEEDS ATTENTION: i-1-VM is blocked until an administrator clears it",
    ], "pool-id", __import__("datetime").datetime.now())
    [(_, success, failure, skipped, blocked)] = recorder.calls
    assert [vm["name"] for vm in success] == ["ok"]
    assert [vm["name"] for vm in skipped] == ["off"]
    assert failure == ["ValueError: boom"]
    # A machine that waits for an administrator is not a new failure.
    assert len(blocked) == 1 and "i-1-VM" in blocked[0]


def test_a_pool_without_hook_posts_nothing(monkeypatch):
    monkeypatch.setattr(notification_sender, "__from_pool_id", lambda pool_id: (SimpleNamespace(name="P"), None))
    notification_sender.on_pool([{"status": "success", "info": {}}], "pool-id", __import__("datetime").datetime.now())
    assert FakeWebhook.sent == []


def test_a_machine_that_was_skipped_does_not_post_that_a_backup_ended(monkeypatch):
    posted = []
    monkeypatch.setattr(task_handler.handle_task_success, "apply_async", lambda **kwargs: posted.append(kwargs))
    sender = SimpleNamespace(request=SimpleNamespace(id="task-1"))
    task_handler.single_backup_success_handler(
        sender=sender, result={"info": {}, "status": "skipped", "reason": "not running"})
    assert posted == []
    task_handler.single_backup_success_handler(sender=sender, result="vda_x_1792431917")
    assert len(posted) == 1


def test_a_failed_single_backup_is_still_posted(monkeypatch):
    posted = []
    monkeypatch.setattr(task_handler.handle_task_failure, "apply_async", lambda **kwargs: posted.append(kwargs))
    task_handler.single_backup_failure_handler(sender=SimpleNamespace(request=SimpleNamespace(id="task-2")))
    assert len(posted) == 1


def test_the_test_of_a_hook_posts_every_kind_of_message(monkeypatch):
    recorder = Recorder()
    monkeypatch.setattr(notification_sender, "__from_hook_id", lambda hook_id: recorder)
    examples = []
    monkeypatch.setattr(notification_sender.notifier, "send_examples", lambda hook_id: examples.append(hook_id))
    notification_sender.test("hook-id")
    # The backup messages and the summaries of a pool, then the other messages of BackROLL.
    assert [call[0] for call in recorder.calls] == ["success", "failure", "pool", "pool", "pool"]
    assert examples == ["hook-id"]


# -- the cleaning of the backups tells the hook of its storage -----------------------------------------------------

@pytest.fixture
def database():
    engine = init_db_connection()
    SQLModel.metadata.create_all(engine)
    migrate_user_table(engine)
    return engine


def test_the_cleaning_posts_to_the_hook_it_was_given_and_never_fails_on_it(database):
    with Session(database) as session:
        hook = ExternalHooks(name="cleanup-hook", value=SECRET)
        session.add(hook)
        session.commit()
        session.refresh(hook)
    cleanup.notify(hook.id, "Cleaning ended: 3 backups deleted")
    [message] = FakeWebhook.sent
    assert message["url"] == SECRET and message["text"] == "Cleaning ended: 3 backups deleted"
    # No hook chosen, or a Slack that does not answer: nothing breaks.
    cleanup.notify(None, "nobody")
    FakeWebhook.fail_with = RuntimeError("Slack is down")
    cleanup.notify(hook.id, "still fine")
    assert len(FakeWebhook.sent) == 1


# -- the address of the webhook is a secret -----------------------------------------------------------------------

@pytest.fixture
def client(database):
    with Session(database) as session:
        for name, role in (("hook-admin", "admin"), ("hook-viewer", "viewer")):
            if password.find_user_by_name(session, name) is None:
                session.add(User(name=name, password_hash=password.hash_password("password1"), role=role))
        session.commit()
    return TestClient(fastapi_app)


def headers(client, name):
    token = client.post("/api/v1/auth/password/login", json={"username": name, "password": "password1"}).json()
    return {"Authorization": f"Bearer {token['access_token']}"}


def stored(database, name):
    with Session(database) as session:
        return session.exec(select(ExternalHooks).where(ExternalHooks.name == name)).one()


def test_the_address_of_the_webhook_is_never_sent_back(client, database):
    admin = headers(client, "hook-admin")
    created = client.post("/api/v1/externalhooks", headers=admin, json={"name": "secret-hook", "value": SECRET})
    assert created.status_code == 201
    assert "SECRETvalue" not in created.text and "hooks.slack.com" in created.text

    listed = json.dumps(external_hooks.api_read_external_hook())
    assert "SECRETvalue" not in listed and "T0AAAAAAA" not in listed
    assert vault.decrypt(stored(database, "secret-hook").value) == SECRET

    hook_id = str(stored(database, "secret-hook").id)
    # The form sends back what it was given: the address is kept.
    masked = json.loads(created.text)["value"]
    kept = client.patch(f"/api/v1/externalhooks/{hook_id}", headers=admin, json={"name": "renamed-hook", "value": masked})
    assert kept.status_code == 200 and "SECRETvalue" not in kept.text
    assert vault.decrypt(stored(database, "renamed-hook").value) == SECRET
    # A new address replaces it.
    new = "https://hooks.slack.com/services/T0CCCCCCC/B0DDDDDDD/newSECRETvalue000"
    client.patch(f"/api/v1/externalhooks/{hook_id}", headers=admin, json={"name": "renamed-hook", "value": new})
    assert vault.decrypt(stored(database, "renamed-hook").value) == new


def test_a_viewer_can_not_test_or_change_a_hook_and_an_administrator_can_test_it(client, database, monkeypatch):
    admin, viewer = headers(client, "hook-admin"), headers(client, "hook-viewer")
    recorder = Recorder()
    monkeypatch.setattr(notification_sender, "__from_hook_id", lambda hook_id: recorder)
    monkeypatch.setattr(notification_sender.notifier, "send_examples", lambda hook_id: 0)
    hook_id = "00000000-0000-0000-0000-000000000001"
    assert client.get(f"/api/v1/externalhooks/{hook_id}/test", headers=viewer).status_code == 403
    assert recorder.calls == []
    assert client.get(f"/api/v1/externalhooks/{hook_id}/test", headers=admin).json() == {"state": "SUCCESS"}
    assert len(recorder.calls) == 5


def test_the_mask_keeps_the_host_and_the_end_so_that_a_hook_can_be_recognized():
    masked = external_hooks.mask_value(SECRET)
    assert masked.startswith("https://hooks.slack.com/") and masked.endswith("ue9")
    assert "services" not in masked and "SECRET" not in masked
    assert external_hooks.mask_value("") == "" and external_hooks.mask_value("short") == external_hooks.MASK


# -- the restores ---------------------------------------------------------------------------------------------------

def test_the_restore_of_a_disk_tells_the_hook_when_it_ends_and_when_it_fails(monkeypatch):
    from app import restore
    ended, exited = [], []
    monkeypatch.setattr(task_handler.handle_task_success, "apply_async", lambda **kwargs: ended.append(kwargs["args"]))
    monkeypatch.setattr(task_handler.handle_task_failure, "apply_async", lambda **kwargs: exited.append(kwargs["args"]))
    sender = SimpleNamespace(request=SimpleNamespace(id="restore-1"))
    task_handler.restore_backup_success_handler(sender=sender)
    task_handler.restore_backup_failure_handler(sender=sender)
    assert ended == [("restore-1", "A new diskfile restore job has ended")]
    # A failure says that the job exited, not that it ended.
    assert exited == [("restore-1", "A new diskfile restore job has exited")]


# -- the summary of a pool -----------------------------------------------------------------------------------------

def test_a_summary_lists_what_failed_and_what_waits_for_an_administrator():
    pool = SimpleNamespace(name="Production")
    received = __import__("datetime").datetime(2026, 10, 19, 21, 0)
    slack.SlackClient(SECRET).on_pool(
        pool, [{"name": "a"}], ["ValueError: disk missing"], received, [{"name": "off"}],
        ["BackupStateError: NEEDS ATTENTION: i-1-VM is blocked"])
    [message] = FakeWebhook.sent
    text = text_of(message)
    assert "*1* Successful" in text and "*1* Failed" in text and "*1* Skipped" in text and "*1* Blocked" in text
    assert "disk missing" in text and "i-1-VM is blocked" in text and "<!channel>" in text


def test_a_machine_that_only_waits_for_an_administrator_does_not_alert_the_channel_again():
    pool = SimpleNamespace(name="Production")
    slack.SlackClient(SECRET).on_pool(pool, [{"name": "a"}], [], __import__("datetime").datetime(2026, 10, 19, 21, 0),
                                      [], ["BackupStateError: NEEDS ATTENTION: i-1-VM is blocked"])
    [message] = FakeWebhook.sent
    assert "*1* Blocked" in text_of(message) and "<!channel>" not in text_of(message)


def test_a_pool_whose_policy_has_no_hook_posts_nothing_and_does_not_fail(monkeypatch):
    from app.routes import backup_policy as policy_route, pool as pool_route
    monkeypatch.setattr(pool_route, "filter_pool_by_id", lambda pool_id: SimpleNamespace(name="P", policy_id="policy"))
    monkeypatch.setattr(policy_route, "filter_policy_by_id", lambda policy_id: SimpleNamespace(externalhook=None))
    # It was a TypeError ("cannot unpack None"): the summary task of every pool without hook ended in FAILURE.
    notification_sender.on_pool([{"status": "success", "info": {"name": "a"}}, "ValueError: boom"], "pool-id",
                                __import__("datetime").datetime.now())
    assert FakeWebhook.sent == []


# -- the play button of a hook ---------------------------------------------------------------------------------------

def test_the_play_button_posts_an_example_of_every_message(monkeypatch):
    engine = init_db_connection()
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        hook = ExternalHooks(name="play-hook", value=SECRET)
        session.add(hook)
        session.commit()
        session.refresh(hook)
    monkeypatch.setattr("time.sleep", lambda seconds: None)
    notification_sender.test(hook.id)
    texts = [text_of(message) for message in FakeWebhook.sent]
    assert len(texts) == 13
    assert all(message["url"] == SECRET for message in FakeWebhook.sent)
    joined = " ".join(texts)
    for expected in ("Notification test message", "Summary of your pool backup job", "Backups stopped",
                     "Disaster recovery restore finished", "Disaster recovery restore failed", "Cleaning started",
                     "Cleaning finished", "Cleaning failed", "Backup storage almost full", "Blocked (waiting for an administrator)",
                     "Skipped (not running)"):
        assert expected in joined, expected
    # The examples are marked as tests, so that nobody takes them for a real alert.
    marked = [message for message in FakeWebhook.sent if "text" in message and message["text"].startswith("[TEST]")]
    assert len(marked) == 8 and all("TEST" in text_of(message) for message in marked)
