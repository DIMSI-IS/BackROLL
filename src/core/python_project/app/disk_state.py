"""The state of the disks of the machines during a backup, kept in the database.

Every step of the backup of a disk is written, so that what happened to a machine can be read afterwards. A
failure that leaves a disk in an uncertain state puts it in NEEDS_ATTENTION, which stops the next backups of the
machine until an administrator, who has looked at the disk, clears it.
"""

from datetime import datetime, timezone

from sqlmodel import Session, select

from app.database import DiskBackupState, init_db_connection

PRECHECK_OK = "PRECHECK_OK"
SNAPSHOT_CREATED = "SNAPSHOT_CREATED"
BORG_DONE = "BORG_DONE"
COMMIT_STARTED = "COMMIT_STARTED"
VERIFIED = "VERIFIED"
CLEANED = "CLEANED"
NEEDS_ATTENTION = "NEEDS_ATTENTION"


def get_engine():
    return init_db_connection()


def set_step(vm_uuid: str, vm_name: str, disk: str, step: str, message: str | None = None) -> bool:
    """Writes the step of a disk. Never raises: a database that does not answer must not stop a backup.

    Returns True when the disk has just started to wait for attention (to tell somebody once, not at every
    refused backup)."""
    try:
        now = datetime.now(timezone.utc)
        with Session(get_engine()) as session:
            row = session.get(DiskBackupState, (str(vm_uuid), disk))
            was_waiting = row is not None and row.step == NEEDS_ATTENTION
            if row is None:
                row = DiskBackupState(vm_uuid=str(vm_uuid), disk=disk, vm_name=vm_name, step=step)
            if step != NEEDS_ATTENTION:
                row.attention_since = None
            elif not was_waiting:
                row.attention_since = now
            row.vm_name, row.step, row.message, row.updated_at = vm_name, step, message, now
            session.add(row)
            session.commit()
        return step == NEEDS_ATTENTION and not was_waiting
    except Exception as exception:
        print(f"Unable to record the step {step} of {vm_name}/{disk}. {exception}")
        return False


def attention_of(vm_uuid: str) -> list[dict]:
    """The disks of a machine that wait for an administrator. Raises if the database does not answer: a backup
    that can not know must not start."""
    with Session(get_engine()) as session:
        rows = session.exec(select(DiskBackupState).where(
            DiskBackupState.vm_uuid == str(vm_uuid), DiskBackupState.step == NEEDS_ATTENTION)).all()
        return [to_dict(row) for row in rows]


def list_attention() -> list[dict]:
    with Session(get_engine()) as session:
        rows = session.exec(select(DiskBackupState).where(DiskBackupState.step == NEEDS_ATTENTION)
                            .order_by(DiskBackupState.attention_since)).all()
        return [to_dict(row) for row in rows]


def clear(vm_uuid: str, disk: str | None = None) -> int:
    """An administrator says that the disks are in order. Returns how many disks were cleared."""
    with Session(get_engine()) as session:
        query = select(DiskBackupState).where(
            DiskBackupState.vm_uuid == str(vm_uuid), DiskBackupState.step == NEEDS_ATTENTION)
        if disk:
            query = query.where(DiskBackupState.disk == disk)
        rows = session.exec(query).all()
        for row in rows:
            row.step, row.attention_since = "CLEARED", None
            row.updated_at = datetime.now(timezone.utc)
            session.add(row)
        session.commit()
        return len(rows)


def to_dict(row: DiskBackupState) -> dict:
    def iso(value):
        return value.replace(tzinfo=timezone.utc).isoformat() if value else None
    return {"vm_uuid": row.vm_uuid, "vm_name": row.vm_name, "disk": row.disk, "step": row.step,
            "message": row.message, "updated_at": iso(row.updated_at), "since": iso(row.attention_since)}
