"""Which machines are backed up: only the ones that are running.

A machine that is off, stopped or changing state is skipped, not failed: nothing is copied, no place of the
limit of simultaneous backups is taken, and no failure is notified every night for a machine that is off on purpose.
"""

RUNNING = "Running"


def skipped(info) -> dict | None:
    """The result of the task when the machine is not backed up, None when it is.

    A description without a state is not skipped: only a state that is known and is not "Running" is."""
    if not isinstance(info, dict):
        return None
    state = info.get("state")
    if state is None or state == RUNNING:
        return None
    reason = f"The virtual machine is not running (state {state}): it is not backed up."
    print(f"[{info.get('name', '?')}] {reason}")
    return {"info": info, "status": "skipped", "reason": reason}
