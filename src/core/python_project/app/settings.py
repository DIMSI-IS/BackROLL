"""Settings of the application that an administrator changes from the interface.

A value saved in the database wins, else the environment variable of the same purpose, else the default.
Values are read each time they are used: a change applies at once, without a restart.
"""

from dataclasses import dataclass
from typing import Callable

from sqlmodel import Session

from app.database import Setting, init_db_connection
from app.environment import get_env_var

DEFAULT_MAX_BACKUP_CONCURRENCY = 8
MAX_RETENTION_DAYS = 3650

BACKUP_CONCURRENCY = "backup_concurrency"
TASK_HISTORY_RETENTION_DAYS = "task_history_retention_days"
AUDIT_RETENTION_DAYS = "audit_retention_days"
JWT_LIFETIME_MINUTES = "jwt_lifetime_minutes"
LOGIN_MAX_ATTEMPTS = "login_max_attempts"
LOGIN_LOCK_MINUTES = "login_lock_minutes"
FILE_BROWSER_TTL_MINUTES = "file_browser_ttl_minutes"
STORAGE_ALERT_PERCENT = "storage_alert_percent"


def get_engine():
    return init_db_connection()


def get_max_backup_concurrency() -> int:
    """Number of processes of the backup worker: no more backups can run at once."""
    value = get_env_var("BACKUP_MAX_CONCURRENCY", allow_undefined=True)
    return int(value) if value and value.isdigit() and int(value) > 0 else DEFAULT_MAX_BACKUP_CONCURRENCY


@dataclass(frozen=True)
class IntegerSetting:
    default: int
    low: int
    high: Callable[[], int]
    # The environment variable that gave the value before it was a setting.
    variable: str | None = None


SETTINGS = {
    BACKUP_CONCURRENCY: IntegerSetting(2, 1, get_max_backup_concurrency),
    TASK_HISTORY_RETENTION_DAYS: IntegerSetting(90, 1, lambda: MAX_RETENTION_DAYS, "TASK_HISTORY_RETENTION_DAYS"),
    AUDIT_RETENTION_DAYS: IntegerSetting(365, 1, lambda: MAX_RETENTION_DAYS, "AUDIT_RETENTION_DAYS"),
    JWT_LIFETIME_MINUTES: IntegerSetting(480, 5, lambda: 43200, "JWT_LIFETIME_MINUTES"),
    LOGIN_MAX_ATTEMPTS: IntegerSetting(5, 1, lambda: 100, "LOGIN_MAX_ATTEMPTS"),
    LOGIN_LOCK_MINUTES: IntegerSetting(15, 1, lambda: 1440, "LOGIN_LOCK_MINUTES"),
    FILE_BROWSER_TTL_MINUTES: IntegerSetting(30, 1, lambda: 1440, "FILE_BROWSER_TTL_MINUTES"),
    STORAGE_ALERT_PERCENT: IntegerSetting(85, 50, lambda: 99),
}


def _saved(key: str) -> int | None:
    # Reading a setting must never stop a login or a backup: without the table, the default is used.
    try:
        with Session(get_engine()) as session:
            setting = session.get(Setting, key)
        return int(setting.value) if setting else None
    except Exception:
        return None


def get_value(key: str) -> int:
    definition = SETTINGS[key]
    value = _saved(key)
    if value is None and definition.variable:
        text = get_env_var(definition.variable, allow_undefined=True)
        value = int(text) if text and text.isdigit() else None
    if value is None:
        value = definition.default
    return max(definition.low, min(value, definition.high()))


def check_value(key: str, value: int):
    if key not in SETTINGS:
        raise ValueError("Unknown setting.")
    definition = SETTINGS[key]
    if not definition.low <= value <= definition.high():
        raise ValueError(f"The value of “{key}” must be between {definition.low} and {definition.high()}.")


def set_value(key: str, value: int):
    check_value(key, value)
    with Session(get_engine()) as session:
        setting = session.get(Setting, key) or Setting(key=key, value="")
        setting.value = str(value)
        session.add(setting)
        session.commit()


def get_all() -> dict[str, int]:
    return {key: get_value(key) for key in SETTINGS}


def get_limits() -> dict[str, dict[str, int]]:
    return {key: {"min": definition.low, "max": definition.high()} for key, definition in SETTINGS.items()}


# Names used by the rest of the application.
def get_backup_concurrency() -> int:
    return get_value(BACKUP_CONCURRENCY)


def set_backup_concurrency(value: int):
    set_value(BACKUP_CONCURRENCY, value)


def get_task_history_retention_days() -> int:
    return get_value(TASK_HISTORY_RETENTION_DAYS)


def get_audit_retention_days() -> int:
    return get_value(AUDIT_RETENTION_DAYS)


def set_retention_days(key: str, value: int):
    if key not in (TASK_HISTORY_RETENTION_DAYS, AUDIT_RETENTION_DAYS):
        raise ValueError("Unknown setting.")
    set_value(key, value)
