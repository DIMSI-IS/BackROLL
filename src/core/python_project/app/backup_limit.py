"""Limits the number of virtual machines backed up at the same time.

The slots are in Redis, shared by all the workers. The limit is read from the settings each time
a backup waits, so a change made in the interface applies to the backups that are waiting too.
"""

import time
from contextlib import contextmanager
from uuid import uuid4

from app import settings
from app.redis import new_redis_client

KEY = "backup-slots"
# A slot of a worker that died is released after this time: a backup stops before (soft time limit of 5400 s).
STALE_SECONDS = 6000
POLL_SECONDS = 5
# A backup that finds no free place goes back to the queue and tries again after this time.
RETRY_SECONDS = 15

# Takes a slot if there is one: removes the stale ones, counts, adds.
ACQUIRE = """
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', ARGV[1] - ARGV[2])
if redis.call('ZCARD', KEYS[1]) < tonumber(ARGV[3]) then
  redis.call('ZADD', KEYS[1], ARGV[1], ARGV[4])
  return 1
end
return 0
"""


def running_count(client=None) -> int:
    client = client or new_redis_client()
    client.zremrangebyscore(KEY, "-inf", time.time() - STALE_SECONDS)
    return client.zcard(KEY)


def try_acquire(label: str, client=None) -> str | None:
    """Takes a place if there is one, without waiting. Returns what to give back, or None."""
    client = client or new_redis_client()
    member = f"{label}:{uuid4()}"
    acquire = client.register_script(ACQUIRE)
    if acquire(keys=[KEY], args=[time.time(), STALE_SECONDS, settings.get_backup_concurrency(), member]):
        return member
    return None


def release(member: str | None, client=None):
    if member:
        (client or new_redis_client()).zrem(KEY, member)


@contextmanager
def slot(label: str, client=None, sleep=time.sleep, poll_seconds: int = POLL_SECONDS):
    """Waits for a free slot, holds it during the block, then gives it back."""
    client = client or new_redis_client()
    member = f"{label}:{uuid4()}"
    acquire = client.register_script(ACQUIRE)
    announced = False
    while not acquire(keys=[KEY], args=[time.time(), STALE_SECONDS,
                                        settings.get_backup_concurrency(), member]):
        if not announced:
            print(f"[{label}] Waiting for a free backup slot "
                  f"({settings.get_backup_concurrency()} backup(s) at the same time).")
            announced = True
        sleep(poll_seconds)
    try:
        yield
    finally:
        client.zrem(KEY, member)


VM_LOCK_SECONDS = 5400


def acquire_vm_lock(client, info) -> str | None:
    """Takes the lock of a machine: one backup or restore at a time on it. Returns the key to delete when done,
    or None when the machine is already locked.

    A single command takes the lock and gives it its expiry: with a look at the key, then a write, then an expiry,
    two tasks could both see a free machine, and a task that died between the write and the expiry left a lock
    that never ended."""
    key = vm_lock_key(info)
    return key if client.set(key, "", nx=True, ex=VM_LOCK_SECONDS) else None


def vm_lock_key(info) -> str:
    """The lock of a machine: one backup at a time on it. It is made from the machine, not from the whole
    description of the task, which changes from one call to the next (the state, the pool...)."""
    identity = info.get('uuid') or info.get('name') if isinstance(info, dict) else None
    return f"vmlock-{identity or info}"
