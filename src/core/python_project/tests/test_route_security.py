"""Non-regression: every route of the API is protected, and the writes are closed to the viewers.

The routes are listed from the application itself: a route added later without a guard fails here, so nobody
has to remember to add it to a list.
"""

import importlib
import re
from pathlib import Path

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel

import app.routes as routes_package
from app.auth import password
from app.database import User, init_db_connection, migrate_user_table
from app.initialized import fastapi_app

# The folders have no __init__.py (app/routes/auth), so the files are listed rather than the packages.
for file in sorted(Path(routes_package.__path__[0]).rglob("*.py")):
    name = "app.routes." + ".".join(file.relative_to(routes_package.__path__[0]).with_suffix("").parts)
    try:
        importlib.import_module(name)
    except ImportError:  # a system library (libvirt) that this machine does not have
        pass

# The only routes that answer without a token: the first setup and the logins.
PUBLIC = {("GET", "/api/v1/auth/setup"), ("POST", "/api/v1/auth/setup"),
          ("POST", "/api/v1/auth/password/login"), ("POST", "/api/v1/auth/cloudstack/login"),
          ("GET", "/api/v1/auth/providers")}
# POST routes that are open to every signed-in person on purpose: one's own password.
OPEN_WRITES = {("POST", "/api/v1/auth/password/change")}
# Reads that are not a plain read of data are still allowed to a viewer: opening a file-browser session of a
# backup is a write (POST) but only editors may do it; the list below stays empty on purpose.
WRITES = {"POST", "PUT", "PATCH", "DELETE"}


def api_routes():
    for route in fastapi_app.routes:
        if isinstance(route, APIRoute) and route.path.startswith("/api/v1"):
            for method in sorted(route.methods - {"HEAD", "OPTIONS"}):
                yield method, route.path


def concrete(path):
    return re.sub(r"\{[^}]+\}", "1", path)


CASES = sorted(set(api_routes()))


@pytest.fixture(scope="module")
def client():
    engine = init_db_connection()
    SQLModel.metadata.create_all(engine)
    migrate_user_table(engine)
    return TestClient(fastapi_app, raise_server_exceptions=False)


@pytest.fixture(scope="module")
def viewer(client):
    # Created in the database: another test file may have made the first administrator already.
    with Session(password.get_engine()) as session:
        if password.find_user_by_name(session, "viewer-sec") is None:
            session.add(User(name="viewer-sec", password_hash=password.hash_password("password1"), role="viewer"))
            session.commit()
    login = client.post("/api/v1/auth/password/login", json={"username": "viewer-sec", "password": "password1"})
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_the_routes_were_found():
    # A change of the way the routes are loaded must not make the checks below empty.
    assert len(CASES) > 60


@pytest.mark.parametrize("method,path", CASES, ids=[f"{m} {p}" for m, p in CASES])
def test_a_request_without_token_is_refused(client, method, path):
    if (method, path) in PUBLIC:
        pytest.skip("public on purpose")
    response = client.request(method, concrete(path), json={})
    assert response.status_code == 401, f"{method} {path} answered {response.status_code} without a token"


WRITE_CASES = [case for case in CASES if case[0] in WRITES]


@pytest.mark.parametrize("method,path", WRITE_CASES, ids=[f"{m} {p}" for m, p in WRITE_CASES])
def test_a_viewer_can_not_write(client, viewer, method, path):
    if (method, path) in PUBLIC | OPEN_WRITES:
        pytest.skip("open to every signed-in person on purpose")
    response = client.request(method, concrete(path), headers=viewer, json={})
    assert response.status_code == 403, f"{method} {path} answered {response.status_code} to a viewer"
