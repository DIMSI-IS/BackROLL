"""Only the front may call the API from a browser."""

import os
import tempfile

import pytest

os.environ["SQLITE_DIRECTORY"] = tempfile.mkdtemp()
os.environ.setdefault("JWT_SECRET", "x" * 40)
os.environ["FRONT_URL"] = "http://192.0.2.245"

from fastapi.testclient import TestClient  # noqa: E402

from app.initialized import fastapi_app, get_allowed_origins, make_cors_app  # noqa: E402


def preflight(client, origin):
    return client.options("/api/v1/auth/setup", headers={
        "Origin": origin, "Access-Control-Request-Method": "GET"})


def test_the_front_is_allowed(monkeypatch):
    monkeypatch.setenv("FRONT_URL", "http://192.0.2.245")
    client = TestClient(make_cors_app(fastapi_app))

    response = preflight(client, "http://192.0.2.245")

    assert response.headers.get("access-control-allow-origin") == "http://192.0.2.245"
    # No cookie is used: nothing needs credentials.
    assert "access-control-allow-credentials" not in response.headers


def test_another_site_is_not_allowed(monkeypatch):
    monkeypatch.setenv("FRONT_URL", "http://192.0.2.245")
    client = TestClient(make_cors_app(fastapi_app))

    response = preflight(client, "https://evil.example")

    assert "access-control-allow-origin" not in response.headers


def test_origins_come_from_the_environment(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "https://a.example/, https://b.example")
    assert get_allowed_origins() == ["https://a.example", "https://b.example"]

    monkeypatch.delenv("CORS_ORIGINS")
    monkeypatch.setenv("FRONT_URL", "")
    assert get_allowed_origins() == []
