"""History of the disaster recovery restores: who restored what, where, and how it went."""

import json
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlmodel import Session, col, func, select, update

from app.auth.password import get_engine
from app.database import DrpRun

MAX_LOG_LENGTH = 4000
MAX_ERROR_LENGTH = 2000
# A run still active after that long was interrupted, for example by a restart of the worker.
INTERRUPTED_AFTER = timedelta(hours=12)


def now() -> datetime:
    return datetime.now(timezone.utc)


def create(user: dict | None, request: dict, connector_name: str | None) -> str:
    run = DrpRun(
        user_id=UUID(str(user["id"])) if user else None,
        username=user["username"] if user else None,
        repository=request["repository"],
        disks=json.dumps(request["disks"]),
        connector_id=UUID(request["connector_id"]),
        connector_name=connector_name,
        domain_id=request.get("domain_id"),
        domain_name=request.get("domain_name"),
        account=request.get("account"),
        vm_name=request["name"],
        status="queued",
    )
    with Session(get_engine()) as session:
        session.add(run)
        session.commit()
        return str(run.id)


def update_run(run_id: str, **fields):
    with Session(get_engine()) as session:
        run = session.get(DrpRun, UUID(run_id))
        if run is None:
            return
        for name, value in fields.items():
            setattr(run, name, value)
        session.add(run)
        session.commit()


def set_task(run_id: str, task_id: str):
    update_run(run_id, task_id=task_id)


def start(run_id: str, task_id: str | None = None):
    update_run(run_id, status="running", task_id=task_id)


def add_step(run_id: str, step: str):
    with Session(get_engine()) as session:
        run = session.get(DrpRun, UUID(run_id))
        if run is None:
            return
        line = f"{now().strftime('%H:%M:%S')} {step}\n"
        run.log = ((run.log or "") + line)[-MAX_LOG_LENGTH:]
        run.step = step[:256]
        session.add(run)
        session.commit()


def finish(run_id: str, status: str, vm_id: str | None = None, error: str | None = None):
    update_run(run_id, status=status, finished_at=now(), vm_id=vm_id,
               error=error[:MAX_ERROR_LENGTH] if error else None)


def mark_interrupted() -> int:
    """Runs that can not be running any more are marked as failed."""
    limit = now() - INTERRUPTED_AFTER
    with Session(get_engine()) as session:
        result = session.exec(
            update(DrpRun)
            .where(col(DrpRun.status).in_(["queued", "running"]), col(DrpRun.created_at) < limit)
            .values(status="failed", finished_at=now(),
                    error="Interrupted: the restore did not finish."))
        session.commit()
        return result.rowcount


def list_runs(limit: int, offset: int, status: str | None = None) -> dict:
    filters = [col(DrpRun.status) == status] if status else []
    with Session(get_engine()) as session:
        total = session.exec(
            select(func.count()).select_from(DrpRun).where(*filters)).one()
        runs = session.exec(select(DrpRun).where(*filters)
                            .order_by(col(DrpRun.created_at).desc())
                            .offset(offset).limit(limit)).all()
        return {"total": total, "items": [run.to_json() for run in runs]}


def get_run(run_id: str) -> dict | None:
    with Session(get_engine()) as session:
        run = session.get(DrpRun, UUID(run_id))
        return run.to_json(with_log=True) if run else None
