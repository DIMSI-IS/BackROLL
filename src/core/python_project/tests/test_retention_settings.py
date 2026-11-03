"""The retention of the audit log and of the history of the tasks is a setting."""

import os

import pytest

os.environ.setdefault("JWT_SECRET", "x" * 40)

from sqlalchemy.pool import StaticPool  # noqa: E402
from sqlmodel import SQLModel, create_engine  # noqa: E402

from app import settings  # noqa: E402


@pytest.fixture(autouse=True)
def database(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(settings, "get_engine", lambda: engine)
    monkeypatch.delenv("AUDIT_RETENTION_DAYS", raising=False)
    monkeypatch.delenv("TASK_HISTORY_RETENTION_DAYS", raising=False)


def test_defaults():
    assert settings.get_task_history_retention_days() == 90
    assert settings.get_audit_retention_days() == 365


def test_the_environment_variable_is_the_default_until_a_value_is_saved(monkeypatch):
    monkeypatch.setenv("AUDIT_RETENTION_DAYS", "30")
    assert settings.get_audit_retention_days() == 30
    settings.set_retention_days(settings.AUDIT_RETENTION_DAYS, 200)
    assert settings.get_audit_retention_days() == 200


def test_values_are_saved_and_bounded():
    settings.set_retention_days(settings.TASK_HISTORY_RETENTION_DAYS, 7)
    assert settings.get_task_history_retention_days() == 7
    for invalid in (0, -5, settings.MAX_RETENTION_DAYS + 1):
        with pytest.raises(ValueError):
            settings.set_retention_days(settings.TASK_HISTORY_RETENTION_DAYS, invalid)
    assert settings.get_task_history_retention_days() == 7


def test_an_unknown_setting_is_refused():
    with pytest.raises(ValueError):
        settings.set_retention_days("something_else", 10)


def test_the_purges_use_the_saved_retention(monkeypatch):
    from app import task_history
    settings.set_retention_days(settings.TASK_HISTORY_RETENTION_DAYS, 5)
    monkeypatch.setattr(task_history, "get_engine", settings.get_engine)
    assert task_history.purge_old_runs() == 0


def test_every_setting_has_a_default_and_bounds():
    values = settings.get_all()
    assert values["jwt_lifetime_minutes"] == 480
    assert values["login_max_attempts"] == 5
    assert values["login_lock_minutes"] == 15
    assert values["file_browser_ttl_minutes"] == 30
    assert values["storage_alert_percent"] == 85
    for key, limits in settings.get_limits().items():
        assert limits["min"] <= values[key] <= limits["max"], key


def test_the_security_settings_are_used_by_the_login(monkeypatch):
    from app.auth import password, token
    settings.set_value(settings.LOGIN_MAX_ATTEMPTS, 3)
    settings.set_value(settings.LOGIN_LOCK_MINUTES, 2)
    settings.set_value(settings.JWT_LIFETIME_MINUTES, 60)
    assert password.get_max_failed_attempts() == 3
    assert password.get_lock_duration().total_seconds() == 120
    assert token.get_lifetime().total_seconds() == 3600


def test_the_file_browser_uses_the_setting():
    from app import file_browser
    settings.set_value(settings.FILE_BROWSER_TTL_MINUTES, 10)
    assert file_browser.get_ttl_seconds() == 600


def test_a_missing_table_gives_the_defaults_instead_of_an_error(monkeypatch):
    def broken():
        raise RuntimeError("database down")
    monkeypatch.setattr(settings, "get_engine", broken)
    assert settings.get_value(settings.LOGIN_MAX_ATTEMPTS) == 5


def test_a_wrong_value_is_refused_whatever_the_setting():
    with pytest.raises(ValueError):
        settings.check_value(settings.JWT_LIFETIME_MINUTES, 1)
    with pytest.raises(ValueError):
        settings.check_value("nothing", 1)
