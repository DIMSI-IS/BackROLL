import os
import tempfile

# Must be set before importing the app.
os.environ["SQLITE_DIRECTORY"] = tempfile.mkdtemp()
os.environ["JWT_SECRET"] = "x" * 40

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlmodel import SQLModel

from app import auth
from app.initialized import fastapi_app
from app.database import init_db_connection, migrate_user_table
from app.routes import users, audit  # noqa: F401
from app.routes.auth import password, cloudstack  # noqa: F401


@fastapi_app.get("/test/read")
def read_route(identity: dict = Depends(auth.verify_token)):
    return identity["username"]


@fastapi_app.post("/test/write")
def write_route(identity: dict = Depends(auth.require_editor)):
    return identity["username"]


@pytest.fixture(scope="module")
def client():
    engine = init_db_connection()
    SQLModel.metadata.create_all(engine)
    migrate_user_table(engine)
    return TestClient(fastapi_app)


def test_first_admin_setup(client):
    assert client.get("/api/v1/auth/setup").json() == {"required": True}
    # Users can not be created, or listed, before the setup.
    assert client.get("/api/v1/users").status_code == 401

    assert client.post("/api/v1/auth/setup",
                       json={"username": "root", "password": "short"}).status_code == 422
    response = client.post("/api/v1/auth/setup",
                           json={"username": "root", "password": "rootroot"})
    assert response.status_code == 201
    assert response.json()["user"]["role"] == "admin"

    assert client.get("/api/v1/auth/setup").json() == {"required": False}
    assert client.post("/api/v1/auth/setup",
                       json={"username": "other", "password": "otherother"}).status_code == 409


def login(client, username, password_):
    return client.post("/api/v1/auth/password/login",
                       json={"username": username, "password": password_})


def headers(client, username, password_):
    token = login(client, username, password_).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_login(client):
    assert login(client, "root", "rootroot").status_code == 200
    assert login(client, "root", "wrong").status_code == 401
    assert login(client, "nobody", "whatever").status_code == 401


def test_anonymous_and_forged_tokens_are_rejected(client):
    assert client.get("/test/read").status_code == 401
    forged = {"Authorization": "Bearer not.a.token"}
    assert client.get("/test/read", headers=forged).status_code == 401


def test_roles(client):
    admin = headers(client, "root", "rootroot")
    for name, role in (("viewer1", "viewer"), ("editor1", "editor")):
        response = client.post("/api/v1/users", headers=admin,
                               json={"name": name, "password": "password1", "role": role})
        assert response.status_code == 201

    viewer = headers(client, "viewer1", "password1")
    editor = headers(client, "editor1", "password1")

    assert client.get("/test/read", headers=viewer).status_code == 200
    assert client.post("/test/write", headers=viewer).status_code == 403
    assert client.post("/test/write", headers=editor).status_code == 200
    assert client.post("/test/write", headers=admin).status_code == 200

    assert client.get("/api/v1/users", headers=editor).status_code == 403
    assert client.get("/api/v1/users", headers=admin).status_code == 200


def test_user_validation(client):
    admin = headers(client, "root", "rootroot")
    assert client.post("/api/v1/users", headers=admin,
                       json={"name": "VIEWER1", "password": "password1"}).status_code == 409
    assert client.post("/api/v1/users", headers=admin,
                       json={"name": "shorty", "password": "short"}).status_code == 422
    assert client.post("/api/v1/users", headers=admin,
                       json={"name": "bad name!", "password": "password1"}).status_code == 422


def test_role_change_and_deactivation_apply_immediately(client):
    admin = headers(client, "root", "rootroot")
    viewer = headers(client, "viewer1", "password1")
    viewer_id = next(user["id"] for user in client.get(
        "/api/v1/users", headers=admin).json() if user["name"] == "viewer1")

    client.patch(f"/api/v1/users/{viewer_id}", headers=admin, json={"role": "editor"})
    assert client.post("/test/write", headers=viewer).status_code == 200

    client.patch(f"/api/v1/users/{viewer_id}", headers=admin, json={"is_active": False})
    assert client.get("/test/read", headers=viewer).status_code == 401
    assert login(client, "viewer1", "password1").status_code == 401


def test_password_change_revokes_old_tokens(client):
    old = headers(client, "editor1", "password1")
    response = client.post("/api/v1/auth/password/change", headers=old,
                           json={"old_password": "password1", "new_password": "newpassword1"})
    assert response.status_code == 200
    assert client.get("/test/read", headers=old).status_code == 401
    new = {"Authorization": f"Bearer {response.json()['access_token']}"}
    assert client.get("/test/read", headers=new).status_code == 200


def test_admin_can_not_lock_themself_out(client):
    admin = headers(client, "root", "rootroot")
    root_id = client.get("/api/v1/auth/me", headers=admin).json()["id"]
    assert client.patch(f"/api/v1/users/{root_id}", headers=admin,
                        json={"role": "viewer"}).status_code == 409
    assert client.delete(f"/api/v1/users/{root_id}", headers=admin).status_code == 409


def test_cloudstack_login_uses_local_users(client):
    response = client.post("/api/v1/auth/cloudstack/login",
                           json={"app_id": "root", "app_secret": "rootroot"})
    assert response.status_code == 200
    token = {"Authorization": f"Bearer {response.json()['access_token']}"}
    assert client.get("/api/v1/auth/cloudstack/test", headers=token).status_code == 200


def test_legacy_user_table_is_migrated_to_admins():
    import sqlalchemy
    engine = sqlalchemy.create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(sqlalchemy.text(
            "CREATE TABLE user (id CHAR(32) PRIMARY KEY, name VARCHAR NOT NULL, password_hash BLOB NOT NULL)"))
        connection.execute(sqlalchemy.text(
            "INSERT INTO user VALUES ('a', 'old', x'00')"))

    migrate_user_table(engine)

    with engine.connect() as connection:
        row = connection.execute(sqlalchemy.text(
            "SELECT role, is_active FROM user")).one()
    assert tuple(row) == ("admin", 1)


def test_audit_log(client):
    admin = headers(client, "root", "rootroot")
    response = client.get("/api/v1/audit?limit=200", headers=admin)
    assert response.status_code == 200
    items = response.json()["items"]
    actions = {item["action"] for item in items}

    assert {"Administrator account created", "Login", "User created",
            "User updated", "Password changed"} <= actions
    # Failed logins are recorded, with the name that was tried.
    assert any(item["action"] == "Login" and item["status_code"] == 401
               and item["username"] == "nobody" for item in items)
    # Denied requests are recorded for the identified user.
    assert any(item["method"] == "POST" and item["path"] == "/test/write"
               and item["status_code"] == 403 and item["username"] == "viewer1"
               for item in items)
    # Reads are not recorded.
    assert not any(item["method"] == "GET" for item in items)
    # Passwords never are.
    assert "password1" not in str(items) and "rootroot" not in str(items)
    assert any("role=editor" in (item["detail"] or "") for item in items)

    only_viewer = client.get("/api/v1/audit?username=viewer1", headers=admin).json()
    assert only_viewer["total"] > 0
    assert all(item["username"] == "viewer1" for item in only_viewer["items"])

    failed = client.get("/api/v1/audit?failed_only=true", headers=admin).json()
    assert failed["total"] > 0
    assert all(item["status_code"] >= 400 for item in failed["items"])

    page = client.get("/api/v1/audit?limit=1&offset=1", headers=admin).json()
    assert len(page["items"]) == 1 and page["total"] == response.json()["total"]


def test_audit_log_is_for_admins(client):
    editor = headers(client, "editor1", "newpassword1")
    assert client.get("/api/v1/audit", headers=editor).status_code == 403
    assert client.get("/api/v1/audit").status_code == 401


def create_user(client, admin, name):
    response = client.post("/api/v1/users", headers=admin,
                           json={"name": name, "password": "goodpassword1", "role": "viewer"})
    assert response.status_code == 201
    return response.json()["id"]


def test_account_is_locked_after_too_many_failures(client):
    admin = headers(client, "root", "rootroot")
    user_id = create_user(client, admin, "lockee")

    for _ in range(5):
        assert login(client, "lockee", "wrong").status_code == 401

    # Locked: even the right password is refused, and nothing says whether it was right.
    locked = login(client, "lockee", "goodpassword1")
    assert locked.status_code == 429
    assert "Retry-After" in locked.headers and "unlock" in locked.json()["detail"]
    assert next(user for user in client.get("/api/v1/users", headers=admin).json()
                if user["id"] == user_id)["locked"] is True

    # An administrator unlocks it.
    assert client.patch(f"/api/v1/users/{user_id}", headers=admin, json={"unlock": True}).status_code == 200
    assert login(client, "lockee", "goodpassword1").status_code == 200


def test_the_lock_ends_by_itself(client, monkeypatch):
    from datetime import timedelta
    from app.auth import password as password_module
    admin = headers(client, "root", "rootroot")
    create_user(client, admin, "patient")
    for _ in range(5):
        login(client, "patient", "wrong")
    assert login(client, "patient", "goodpassword1").status_code == 429

    monkeypatch.setattr(password_module, "utcnow",
                        lambda: password_module.datetime.now(password_module.timezone.utc) + timedelta(minutes=16))

    assert login(client, "patient", "goodpassword1").status_code == 200


def test_a_success_resets_the_counter(client):
    admin = headers(client, "root", "rootroot")
    create_user(client, admin, "careful")
    for _ in range(4):
        login(client, "careful", "wrong")
    assert login(client, "careful", "goodpassword1").status_code == 200
    # The four failures are forgotten: four more do not lock.
    for _ in range(4):
        login(client, "careful", "wrong")
    assert login(client, "careful", "goodpassword1").status_code == 200


def test_a_password_reset_unlocks(client):
    admin = headers(client, "root", "rootroot")
    user_id = create_user(client, admin, "forgetful")
    for _ in range(5):
        login(client, "forgetful", "wrong")
    assert login(client, "forgetful", "goodpassword1").status_code == 429

    client.patch(f"/api/v1/users/{user_id}", headers=admin, json={"password": "anotherpassword1"})

    assert login(client, "forgetful", "anotherpassword1").status_code == 200


def test_unknown_users_are_not_revealed_by_the_lock(client):
    for _ in range(8):
        assert login(client, "ghost", "wrong").status_code == 401
