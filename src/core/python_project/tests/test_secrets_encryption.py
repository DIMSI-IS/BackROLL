"""The secret key of the CloudStack connectors and the address of the webhooks are encrypted in the database.

BackROLL still reads them (it talks to CloudStack and posts in Slack), the browser never gets them, and a database
stored before the encryption is encrypted at the start.
"""

import json
from uuid import UUID

import pytest
from sqlalchemy import text
from sqlmodel import Session, SQLModel

pytest.importorskip("libvirt")

from app import database, notifier, vault  # noqa: E402
from app.cloudstack import endpoint  # noqa: E402
from app.database import Connectors, ExternalHooks  # noqa: E402
from app.hooks import notification_sender  # noqa: E402
from app.routes import connectors, external_hooks  # noqa: E402

API_KEY = "EXAMPLE-api-key-0123456789abcdefghijklmn"
SECRET = "EXAMPLE-secret-key-0123456789abcdefghij"
WEBHOOK = "https://hooks.slack.com/services/T0AAAAAAA/B0BBBBBBB/xyz123SECRETvalue9"


@pytest.fixture
def engine():
    engine = database.init_db_connection()
    SQLModel.metadata.create_all(engine)
    return engine


def raw(engine, table, column, identifier):
    """The value as the database holds it, not as the application reads it."""
    with engine.connect() as connection:
        return connection.execute(text(f"SELECT {column} FROM {table} WHERE id = :id"),
                                  {"id": str(identifier).replace("-", "")}).scalar()


def insert_in_clear(engine, table, values):
    columns = ", ".join(values)
    marks = ", ".join(f":{name}" for name in values)
    with engine.begin() as connection:
        connection.execute(text(f"INSERT INTO {table} ({columns}) VALUES ({marks})"), values)


# -- the connectors ----------------------------------------------------------------------------------------------

def test_the_secret_key_of_a_connector_is_stored_encrypted_and_read_back(engine):
    created = connectors.api_create_connector.run("cs", "http://cs/client/api", API_KEY, SECRET)

    stored = raw(engine, "connectors", "password", created["id"])
    assert stored.startswith(vault.PREFIX) and SECRET not in stored
    assert vault.decrypt(connectors.filter_connector_by_id(created["id"]).password) == SECRET
    assert created["has_password"] is True and SECRET not in json.dumps(created)


def test_cloudstack_receives_the_secret_in_clear_and_never_the_encrypted_one(engine, monkeypatch):
    created = connectors.api_create_connector.run("cs", "http://cs/client/api", API_KEY, SECRET)
    received = {}

    class FakeCloudStack:
        def __init__(self, **arguments):
            received.update(arguments)

    monkeypatch.setattr(endpoint, "CloudStack", FakeCloudStack)

    endpoint.cloudstack_connector(connectors.filter_connector_by_id(created["id"]))

    assert received["secret"] == SECRET and received["key"] == API_KEY


def test_updating_a_connector_encrypts_the_new_secret_and_keeps_the_old_one_without_a_new_one(engine):
    created = connectors.api_create_connector.run("cs", "http://cs/client/api", API_KEY, SECRET)
    before = raw(engine, "connectors", "password", created["id"])

    connectors.api_update_connector.run(created["id"], "renamed", "http://cs/client/api", created["login"], "")
    assert raw(engine, "connectors", "password", created["id"]) == before

    connectors.api_update_connector.run(created["id"], "renamed", "http://cs/client/api", created["login"], "new-secret")
    changed = raw(engine, "connectors", "password", created["id"])
    assert changed != before and changed.startswith(vault.PREFIX) and "new-secret" not in changed
    assert vault.decrypt(connectors.filter_connector_by_id(created["id"]).password) == "new-secret"


# -- the webhooks ------------------------------------------------------------------------------------------------

def test_the_address_of_a_webhook_is_stored_encrypted_and_shown_masked(engine):
    created = external_hooks.api_create_external_hook.run("slack", WEBHOOK)

    stored = raw(engine, "externalhooks", "value", created["id"])
    assert stored.startswith(vault.PREFIX) and "hooks.slack.com" not in stored
    assert "SECRETvalue" not in json.dumps(created) and created["value"].startswith("https://hooks.slack.com/")
    listed = json.dumps(external_hooks.api_read_external_hook.run())
    assert "SECRETvalue" not in listed and "T0AAAAAAA" not in listed


def test_updating_a_webhook_with_the_masked_address_keeps_it_and_a_new_one_is_encrypted(engine):
    created = external_hooks.api_create_external_hook.run("slack", WEBHOOK)
    before = raw(engine, "externalhooks", "value", created["id"])

    external_hooks.api_update_external_hook.run(created["id"], "renamed", created["value"])
    assert raw(engine, "externalhooks", "value", created["id"]) == before

    new = "https://hooks.slack.com/services/T0CCCCCCC/B0DDDDDDD/newSECRETvalue000"
    external_hooks.api_update_external_hook.run(created["id"], "renamed", new)
    changed = raw(engine, "externalhooks", "value", created["id"])
    assert changed.startswith(vault.PREFIX) and "newSECRET" not in changed
    assert vault.decrypt(changed) == new


def test_slack_is_posted_to_the_decrypted_address(engine, monkeypatch):
    created = external_hooks.api_create_external_hook.run("slack", WEBHOOK)
    posted = []

    class FakeWebhook:
        def __init__(self, url, *args, **kwargs):
            posted.append(url)

        def send(self, **message):
            pass

    monkeypatch.setattr("slack_sdk.webhook.WebhookClient", FakeWebhook)
    monkeypatch.setattr(notification_sender, "SlackClient", lambda url: posted.append(url))

    notifier.send(created["id"], "hello")
    getattr(notification_sender, "__from_hook_id")(created["id"])

    assert posted == [WEBHOOK, WEBHOOK]


def test_a_hook_whose_key_changed_does_not_break_the_notification(engine, monkeypatch):
    monkeypatch.setenv("SECRETS_KEY", "first-key")
    created = external_hooks.api_create_external_hook.run("slack", WEBHOOK)
    monkeypatch.setenv("SECRETS_KEY", "second-key")

    notifier.send(created["id"], "hello")  # best effort: nothing is raised

    with pytest.raises(vault.SecretError, match="Type it again"):
        vault.decrypt(raw(engine, "externalhooks", "value", created["id"]))
    # The list of the hooks stays usable, with this address hidden, so that it can be typed again.
    listed = {item["id"]: item["value"] for item in external_hooks.api_read_external_hook.run()}
    assert listed[created["id"]] == external_hooks.MASK
    monkeypatch.setenv("SECRETS_KEY", "first-key")
    external_hooks.api_update_external_hook.run(created["id"], "renamed", WEBHOOK)
    monkeypatch.delenv("SECRETS_KEY")
    with Session(engine) as session:
        session.delete(session.get(ExternalHooks, UUID(created["id"])))
        session.commit()


# -- a database stored before the encryption ----------------------------------------------------------------------

def test_the_secrets_stored_in_clear_are_encrypted_at_the_start_and_still_work(engine):
    insert_in_clear(engine, "connectors", {"id": "a" * 32, "name": "old", "url": "http://cs", "login": API_KEY,
                                           "password": SECRET})
    insert_in_clear(engine, "externalhooks", {"id": "b" * 32, "name": "old-hook", "value": WEBHOOK})

    database.migrate_secrets(engine)

    assert raw(engine, "connectors", "password", "a" * 32).startswith(vault.PREFIX)
    assert raw(engine, "externalhooks", "value", "b" * 32).startswith(vault.PREFIX)
    with Session(engine) as session:
        assert vault.decrypt(session.get(Connectors, UUID("a" * 32)).password) == SECRET
        assert vault.decrypt(session.get(ExternalHooks, UUID("b" * 32)).value) == WEBHOOK


def test_the_migration_can_run_twice_without_encrypting_twice(engine):
    insert_in_clear(engine, "externalhooks", {"id": "c" * 32, "name": "twice", "value": WEBHOOK})

    database.migrate_secrets(engine)
    once = raw(engine, "externalhooks", "value", "c" * 32)
    database.migrate_secrets(engine)

    assert raw(engine, "externalhooks", "value", "c" * 32) == once
    assert vault.decrypt(once) == WEBHOOK


def test_without_a_key_the_migration_changes_nothing_and_the_values_are_still_read(engine, monkeypatch):
    insert_in_clear(engine, "externalhooks", {"id": "d" * 32, "name": "nokey", "value": WEBHOOK})
    monkeypatch.delenv("SECRETS_KEY", raising=False)
    monkeypatch.delenv("JWT_SECRET", raising=False)

    database.migrate_secrets(engine)

    assert raw(engine, "externalhooks", "value", "d" * 32) == WEBHOOK
    assert vault.decrypt(WEBHOOK) == WEBHOOK
