from fastapi import Depends, Query

from app import auth, protection
from app.initialized import fastapi_app
from app.routes.file_browser import get_storage_paths


@fastapi_app.get("/api/v1/dashboard/protection", status_code=200)
def get_protection(max_age_hours: int = Query(48, ge=1, le=24 * 365),
                   identity: dict = Depends(auth.require_viewer)):
    """The last backup of every virtual machine that has a repository, to show which ones are at risk."""
    return {"max_age_hours": max_age_hours,
            "repositories": protection.get_protection(get_storage_paths(), max_age_hours)}
