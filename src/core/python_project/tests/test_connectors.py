"""The API key and the secret of the connectors are never sent to the browser."""

import os
import tempfile

import pytest

os.environ["SQLITE_DIRECTORY"] = tempfile.mkdtemp()
os.environ.setdefault("JWT_SECRET", "x" * 40)

connectors = pytest.importorskip("app.routes.connectors")

from sqlmodel import SQLModel  # noqa: E402

from app import database, vault  # noqa: E402

API_KEY = "EXAMPLE-api-key-0123456789abcdefghijklmn"
SECRET = "EXAMPLE-secret-key-0123456789abcdefghij"


@pytest.fixture(autouse=True)
def tables():
    SQLModel.metadata.create_all(database.init_db_connection())


def create():
    return connectors.api_create_connector.run("cs", "http://cs/client/api", API_KEY, SECRET)


def test_nothing_secret_is_returned_when_creating():
    created = create()

    assert API_KEY not in str(created) and SECRET not in str(created)
    assert created["has_password"] is True and created["login"].endswith(connectors.MASK)


def test_nothing_secret_is_in_the_list():
    create()

    listed = connectors.api_retrieve_connectors.run()

    assert listed and API_KEY not in str(listed) and SECRET not in str(listed)
    assert all("password" not in item for item in listed)


def test_the_stored_credentials_are_still_complete():
    created = create()

    stored = connectors.filter_connector_by_id(created["id"])

    # BackROLL itself needs them to talk to CloudStack.
    assert stored.login == API_KEY and vault.decrypt(stored.password) == SECRET


def test_an_update_without_secret_keeps_them():
    created = create()

    connectors.api_update_connector.run(created["id"], "renamed", "http://cs/client/api", created["login"], "")

    stored = connectors.filter_connector_by_id(created["id"])
    assert stored.name == "renamed" and stored.login == API_KEY and vault.decrypt(stored.password) == SECRET


def test_an_update_replaces_what_is_given():
    created = create()

    connectors.api_update_connector.run(created["id"], "cs", "http://cs/client/api", "NEWKEY12345678", "new-secret")

    stored = connectors.filter_connector_by_id(created["id"])
    assert stored.login == "NEWKEY12345678" and vault.decrypt(stored.password) == "new-secret"
