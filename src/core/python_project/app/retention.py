"""Deletes the audit entries and the history of the tasks that are older than their retention."""

import threading
import time
from logging import Logger

from app import audit, task_history
from app.logging import logged

INTERVAL_SECONDS = 6 * 3600


@logged(bounds=False)
def clean(logger: Logger):
    for purge in (audit.purge_old_entries, task_history.purge_old_runs):
        try:
            purge()
        except Exception as exception:
            logger.error(f"Unable to clean the old entries. {exception}")


def start_cleaner():
    """A first cleaning now, then one every six hours. The retention is read each time:
    a change in the settings applies at the next cleaning."""
    def loop():
        while True:
            clean()
            time.sleep(INTERVAL_SECONDS)

    threading.Thread(target=loop, daemon=True).start()
