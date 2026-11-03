"""Tells the hook (Slack) of a backup storage when its disk is almost full.

One message each time the usage crosses the limit set in the settings, and none while it stays above: the alert is
armed again once the usage is back under the limit. The hook is the one chosen for the storage in Tasks > Clean backup.
A storage without a hook is not told about: it is tried again at each check, so the message is sent as soon as a hook is
chosen. A storage that is not mounted is skipped: the dashboard already says so.
"""

import shutil
import threading
import time
from datetime import datetime, timezone
from logging import Logger

from sqlmodel import Session, select

from app import notifier, settings
from app.database import Setting, Storage, StorageCleanup, init_db_connection
from app.logging import logged

INTERVAL_SECONDS = 15 * 60
# The alert is armed again when the usage is this many points under the limit, so that a disk that goes up and down
# around the limit does not post at every check.
HYSTERESIS_POINTS = 3


def flag_key(storage: Storage) -> str:
    return f"storage_alert:{storage.id}"


def usage_of(path: str) -> tuple[float, int, int] | None:
    """The percentage used, the free bytes and the total bytes of the disk of a storage, or None."""
    try:
        usage = shutil.disk_usage(path)
    except OSError:
        return None
    if not usage.total:
        return None
    return (usage.total - usage.free) * 100 / usage.total, usage.free, usage.total


def check_storage(session: Session, storage: Storage, limit: int, logger: Logger):
    usage = usage_of(storage.path)
    if usage is None:
        return
    percent, free, total = usage
    flag = session.get(Setting, flag_key(storage))
    if percent >= limit and flag is None:
        cleanup = session.get(StorageCleanup, storage.id)
        if cleanup is None or not cleanup.hook_id:
            return
        sent = notifier.send(cleanup.hook_id, notifier.storage_space_message(storage.name, percent, free, total, limit),
                             notifier.storage_space_blocks(storage.name, percent, free, total, limit))
        if sent:
            session.add(Setting(key=flag_key(storage), value=datetime.now(timezone.utc).isoformat()))
            session.commit()
            logger.warning(f"The storage {storage.name} is {percent:.0f} % full: the hook has been told.")
    elif flag is not None and percent < limit - HYSTERESIS_POINTS:
        session.delete(flag)
        session.commit()


@logged(bounds=False)
def check(logger: Logger):
    limit = settings.get_value(settings.STORAGE_ALERT_PERCENT)
    with Session(init_db_connection()) as session:
        for storage in session.exec(select(Storage)).all():
            try:
                check_storage(session, storage, limit, logger)
            except Exception as exception:
                logger.error(f"Unable to check the free space of the storage {storage.name}. {exception}")


def start_checker():
    """A first check now, then one every 15 minutes. The limit is read each time: a change applies at the next check."""
    def loop():
        while True:
            check()
            time.sleep(INTERVAL_SECONDS)

    threading.Thread(target=loop, daemon=True).start()
