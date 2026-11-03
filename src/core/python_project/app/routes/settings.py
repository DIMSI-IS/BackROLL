from fastapi import Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app import audit, auth, backup_limit, settings
from app.initialized import fastapi_app


def current_settings() -> dict:
    return {
        **settings.get_all(),
        # The bounds of each value, to build the form.
        "limits": settings.get_limits(),
        "backups_running": backup_limit.running_count(),
    }


class SettingsUpdate(BaseModel):
    # What is not given is left as it is. The bounds are checked by the settings.
    backup_concurrency: int | None = Field(default=None, ge=0, le=100000)
    task_history_retention_days: int | None = Field(default=None, ge=0, le=100000)
    audit_retention_days: int | None = Field(default=None, ge=0, le=100000)
    jwt_lifetime_minutes: int | None = Field(default=None, ge=0, le=100000000)
    login_max_attempts: int | None = Field(default=None, ge=0, le=100000)
    login_lock_minutes: int | None = Field(default=None, ge=0, le=100000)
    file_browser_ttl_minutes: int | None = Field(default=None, ge=0, le=100000)
    storage_alert_percent: int | None = Field(default=None, ge=0, le=100000)


@fastapi_app.get("/api/v1/settings", status_code=200)
def get_settings(identity: dict = Depends(auth.require_admin)):
    return current_settings()


@fastapi_app.put("/api/v1/settings", status_code=200)
def update_settings(item: SettingsUpdate, request: Request,
                    identity: dict = Depends(auth.require_admin)):
    updates = {key: value for key, value in item.model_dump().items() if value is not None}
    before = settings.get_all()
    try:
        # Everything is checked before anything is saved.
        for key, value in updates.items():
            settings.check_value(key, value)
        for key, value in updates.items():
            settings.set_value(key, value)
    except ValueError as exception:
        raise HTTPException(422, str(exception))
    after = settings.get_all()
    changes = [f"{key}={before[key]}->{after[key]}" for key in after if before[key] != after[key]]
    audit.set_detail(request, ", ".join(changes) or "no change")
    return current_settings()
