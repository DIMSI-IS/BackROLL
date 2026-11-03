"""The cases limit of the login tokens: whatever is sent in `Authorization`, the answer is a refusal (401), never a
server error and never an access."""

import base64
import json
import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel

os.environ.setdefault("JWT_SECRET", "x" * 40)

import app.routes as routes_package  # noqa: E402
from app.auth import password, token  # noqa: E402
from app.database import User, init_db_connection, migrate_user_table  # noqa: E402
from app.initialized import fastapi_app  # noqa: E402

import importlib  # noqa: E402
from pathlib import Path  # noqa: E402

for file in sorted(Path(routes_package.__path__[0]).rglob("*.py")):
    name = "app.routes." + ".".join(file.relative_to(routes_package.__path__[0]).with_suffix("").parts)
    try:
        importlib.import_module(name)
    except ImportError:  # a system library that this machine does not have
        pass

PATH = "/api/v1/users"   # a route for the administrators: the strictest check


@pytest.fixture(scope="module")
def client():
    engine = init_db_connection()
    SQLModel.metadata.create_all(engine)
    migrate_user_table(engine)
    return TestClient(fastapi_app, raise_server_exceptions=False)


def make_user(name, role="admin", active=True):
    with Session(password.get_engine()) as session:
        user = password.find_user_by_name(session, name)
        if user is None:
            user = User(name=name, password_hash=password.hash_password("password1"), role=role, is_active=active)
            session.add(user)
            session.commit()
            session.refresh(user)
        return user


def bearer(value):
    return {"Authorization": f"Bearer {value}"}


def claims_of(user, **changes):
    now = datetime.now(timezone.utc)
    claims = {"sub": str(user.id), "username": user.name, "role": user.role,
              "pwd": token.password_fingerprint(user.password_hash), "iat": now, "exp": now + timedelta(hours=1)}
    claims.update(changes)
    return {key: value for key, value in claims.items() if value is not None}


def test_a_valid_token_is_accepted(client):
    user = make_user("scenario-admin")
    assert client.get(PATH, headers=bearer(token.create(user))).status_code == 200


def test_an_expired_token_is_refused(client):
    user = make_user("scenario-admin")
    expired = jwt.encode(claims_of(user, exp=datetime.now(timezone.utc) - timedelta(seconds=5)),
                         os.environ["JWT_SECRET"], algorithm="HS256")
    assert client.get(PATH, headers=bearer(expired)).status_code == 401


def test_a_token_signed_with_another_secret_is_refused(client):
    user = make_user("scenario-admin")
    forged = jwt.encode(claims_of(user), "another-secret-that-is-long-enough-1234567890", algorithm="HS256")
    assert client.get(PATH, headers=bearer(forged)).status_code == 401


def test_a_token_without_signature_is_refused(client):
    """The `none` algorithm: a token that anybody can write."""
    user = make_user("scenario-admin")

    def part(data):
        return base64.urlsafe_b64encode(json.dumps(data, default=str).encode()).rstrip(b"=").decode()
    unsigned = f"{part({'alg': 'none', 'typ': 'JWT'})}.{part(claims_of(user, iat=None, exp=9999999999))}."
    assert client.get(PATH, headers=bearer(unsigned)).status_code == 401


def test_a_token_signed_with_another_algorithm_is_refused(client):
    user = make_user("scenario-admin")
    other = jwt.encode(claims_of(user), os.environ["JWT_SECRET"] * 2, algorithm="HS512")
    assert client.get(PATH, headers=bearer(other)).status_code == 401


@pytest.mark.parametrize("missing", ["sub", "exp", "pwd"])
def test_a_signed_token_without_a_required_claim_is_refused_not_a_server_error(client, missing):
    user = make_user("scenario-admin")
    incomplete = jwt.encode(claims_of(user, **{missing: None}), os.environ["JWT_SECRET"], algorithm="HS256")
    assert client.get(PATH, headers=bearer(incomplete)).status_code == 401


def test_a_token_whose_subject_is_not_an_identifier_is_refused(client):
    user = make_user("scenario-admin")
    bad = jwt.encode(claims_of(user, sub="not-a-uuid"), os.environ["JWT_SECRET"], algorithm="HS256")
    assert client.get(PATH, headers=bearer(bad)).status_code == 401


def test_a_token_of_a_user_that_does_not_exist_any_more_is_refused(client):
    ghost = type("Ghost", (), {"id": uuid4(), "name": "ghost", "role": "admin", "password_hash": b"x"})()
    assert client.get(PATH, headers=bearer(token.create(ghost))).status_code == 401


def test_a_token_of_a_deactivated_user_is_refused(client):
    user = make_user("scenario-disabled", role="admin", active=False)
    assert client.get(PATH, headers=bearer(token.create(user))).status_code == 401


@pytest.mark.parametrize("header", ["", "Bearer", "Bearer ", "Bearer a.b.c", "Basic abc", "bearer", "Bearer " + "A" * 5000,
                                    "Bearer null", "Bearer undefined"])
def test_a_header_that_is_not_a_token_is_refused_not_a_server_error(client, header):
    response = client.get(PATH, headers={"Authorization": header})
    assert response.status_code in (401, 403), (header[:30], response.status_code)


def test_the_role_written_in_the_token_does_not_count(client):
    """The role comes from the database at each request: a token that says admin gives nothing to a viewer."""
    viewer = make_user("scenario-viewer", role="viewer")
    lying = jwt.encode(claims_of(viewer, role="admin"), os.environ["JWT_SECRET"], algorithm="HS256")
    assert client.get(PATH, headers=bearer(lying)).status_code == 403
