"""A backup storage that is almost full tells its Slack hook once, and again only after it went back under the limit.

A fake Slack client records what would be posted; no disk is really filled: the usage of the disk is replaced.
"""

import os
from collections import namedtuple
from types import SimpleNamespace

import pytest
from sqlmodel import Session, SQLModel, select

pytest.importorskip("libvirt")

from app import notifier, settings, storage_alert  # noqa: E402
from app.database import ExternalHooks, Setting, Storage, StorageCleanup, init_db_connection  # noqa: E402

Usage = namedtuple("Usage", "total used free")
GIB = 1024 ** 3
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
    monkeypatch.setenv("FRONT_URL", "https://backroll.example")


@pytest.fixture
def engine():
    engine = init_db_connection()
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        for model in (Setting, StorageCleanup, Storage, ExternalHooks):
            for row in session.exec(select(model)).all():
                session.delete(row)
        session.commit()
    return engine


def make_storage(engine, name="BACKUP_STORAGE", with_hook=True):
    with Session(engine) as session:
        storage = Storage(name=name, path=f"/mnt/{name}")
        session.add(storage)
        session.commit()
        session.refresh(storage)
        storage_id = storage.id
        hook = None
        if with_hook:
            hook = ExternalHooks(name="alerts", value=SECRET)
            session.add(hook)
            session.commit()
            session.refresh(hook)
        session.add(StorageCleanup(storage_id=storage.id, hook_id=hook.id if hook else None))
        session.commit()
        # What the tests need, read while the session is open: the row is detached after the commit.
        return SimpleNamespace(id=storage_id, name=name)


def disk(monkeypatch, used_percent, total=1000 * GIB):
    used = int(total * used_percent / 100)
    monkeypatch.setattr(storage_alert.shutil, "disk_usage", lambda path: Usage(total, used, total - used))


def text(message):
    return message["text"] + str(message.get("blocks", ""))


def test_a_storage_above_the_limit_tells_its_hook_once(engine, monkeypatch):
    make_storage(engine)
    disk(monkeypatch, 90)

    storage_alert.check()
    storage_alert.check()
    storage_alert.check()

    [message] = FakeWebhook.sent
    assert message["url"] == SECRET
    assert "BACKUP_STORAGE" in text(message) and "90 %" in text(message) and "<!channel>" in message["text"]
    # The sizes are written to be read, with the limit of the settings.
    assert "GiB" in text(message) and "85 %" in text(message)


def test_a_storage_under_the_limit_says_nothing(engine, monkeypatch):
    make_storage(engine)
    disk(monkeypatch, 60)

    storage_alert.check()

    assert FakeWebhook.sent == []


def test_it_is_told_again_only_after_the_storage_went_back_under_the_limit(engine, monkeypatch):
    make_storage(engine)
    disk(monkeypatch, 90)
    storage_alert.check()
    # Slightly under the limit, but within the margin: the alert stays disarmed, no message at every check.
    disk(monkeypatch, 84)
    storage_alert.check()
    disk(monkeypatch, 86)
    storage_alert.check()
    assert len(FakeWebhook.sent) == 1
    # Well under the limit: armed again, and the next crossing is told.
    disk(monkeypatch, 70)
    storage_alert.check()
    disk(monkeypatch, 92)
    storage_alert.check()
    assert len(FakeWebhook.sent) == 2


def test_the_limit_of_the_settings_is_used_and_a_change_applies_at_the_next_check(engine, monkeypatch):
    make_storage(engine)
    disk(monkeypatch, 80)
    storage_alert.check()
    assert FakeWebhook.sent == []

    settings.set_value(settings.STORAGE_ALERT_PERCENT, 75)
    storage_alert.check()

    assert len(FakeWebhook.sent) == 1 and "75 %" in text(FakeWebhook.sent[0])
    settings.set_value(settings.STORAGE_ALERT_PERCENT, 85)


def test_a_storage_without_a_hook_is_not_told_about_until_a_hook_is_chosen(engine, monkeypatch):
    storage = make_storage(engine, with_hook=False)
    disk(monkeypatch, 95)
    storage_alert.check()
    assert FakeWebhook.sent == []

    with Session(engine) as session:
        hook = ExternalHooks(name="late", value=SECRET)
        session.add(hook)
        session.commit()
        session.refresh(hook)
        cleanup = session.get(StorageCleanup, storage.id)
        cleanup.hook_id = hook.id
        session.add(cleanup)
        session.commit()
    storage_alert.check()

    assert len(FakeWebhook.sent) == 1


def test_a_message_that_slack_did_not_take_is_sent_again_at_the_next_check(engine, monkeypatch):
    make_storage(engine)
    disk(monkeypatch, 90)
    FakeWebhook.fail_with = RuntimeError("Slack is down")
    storage_alert.check()
    assert FakeWebhook.sent == []

    FakeWebhook.fail_with = None
    storage_alert.check()

    assert len(FakeWebhook.sent) == 1


def test_a_storage_that_is_not_mounted_is_skipped_and_does_not_stop_the_others(engine, monkeypatch):
    make_storage(engine, "NOT_MOUNTED")
    full = make_storage(engine, "FULL_ONE")

    def usage(path):
        if path.endswith("NOT_MOUNTED"):
            raise FileNotFoundError(path)
        return Usage(1000 * GIB, 900 * GIB, 100 * GIB)

    monkeypatch.setattr(storage_alert.shutil, "disk_usage", usage)

    storage_alert.check()

    [message] = FakeWebhook.sent
    assert "FULL_ONE" in text(message) and full.name == "FULL_ONE"


def test_the_limit_is_a_setting_with_bounds(engine):
    assert settings.get_value(settings.STORAGE_ALERT_PERCENT) == 85
    with pytest.raises(ValueError):
        settings.check_value(settings.STORAGE_ALERT_PERCENT, 100)
    with pytest.raises(ValueError):
        settings.check_value(settings.STORAGE_ALERT_PERCENT, 10)


def test_the_message_is_one_of_the_examples_of_the_hook_test():
    titles = [title for title, _ in notifier.example_messages()]
    assert "Backup storage almost full" in titles
    assert os.environ.get("JWT_SECRET")
