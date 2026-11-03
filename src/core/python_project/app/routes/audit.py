from fastapi import Depends, Query, Request
from sqlmodel import Session, col, func, select
from starlette.concurrency import run_in_threadpool

from app import audit, auth
from app.auth.password import get_engine
from app.database import AuditLog
from app.initialized import fastapi_app


@fastapi_app.middleware("http")
async def audit_middleware(request: Request, call_next):
    response = await call_next(request)
    # The route and the identity are known once the request is handled.
    await run_in_threadpool(audit.record, request, response.status_code)
    return response


@fastapi_app.get("/api/v1/audit", status_code=200)
def list_audit_log(
    username: str | None = Query(None, max_length=64),
    action: str | None = Query(None, max_length=128),
    failed_only: bool = False,
    source: str | None = Query(None, pattern="^(local|ad)$"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    identity: dict = Depends(auth.require_admin),
):
    filters = []
    if username:
        filters.append(col(AuditLog.username).contains(username))
    if action:
        filters.append(col(AuditLog.action).contains(action))
    if failed_only:
        filters.append(col(AuditLog.status_code) >= 400)
    if source:
        filters.append(col(AuditLog.source) == source)

    with Session(get_engine()) as session:
        total = session.exec(
            select(func.count()).select_from(AuditLog).where(*filters)).one()
        entries = session.exec(select(AuditLog).where(*filters)
                               .order_by(col(AuditLog.created_at).desc())
                               .offset(offset).limit(limit)).all()
        return {"total": total, "items": [entry.to_json() for entry in entries]}
