"""The limit of simultaneous backups: the setting, its bounds, and the slots with a Redis that is not real."""

import os
import threading
import time

import pytest

os.environ.setdefault("JWT_SECRET", "x" * 40)

from sqlmodel import SQLModel, create_engine  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app import backup_limit, settings  # noqa: E402


@pytest.fixture(autouse=True)
def database(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(settings, "get_engine", lambda: engine)
    monkeypatch.delenv("BACKUP_MAX_CONCURRENCY", raising=False)


class FakeRedis:
    """Only what the slots use. The script is run in Python, with the same rules."""

    def __init__(self):
        self.members = {}
        self.lock = threading.Lock()

    def register_script(self, script):
        def acquire(keys, args):
            now, stale, limit, member = float(args[0]), float(args[1]), int(args[2]), args[3]
            with self.lock:
                self.members = {m: t for m, t in self.members.items() if t > now - stale}
                if len(self.members) < limit:
                    self.members[member] = now
                    return 1
                return 0
        return acquire

    def zrem(self, key, member):
        with self.lock:
            self.members.pop(member, None)

    def zremrangebyscore(self, key, low, high):
        with self.lock:
            self.members = {m: t for m, t in self.members.items() if t > float(high)}

    def zcard(self, key):
        return len(self.members)


def test_default_and_bounds():
    assert settings.get_backup_concurrency() == 2
    settings.set_backup_concurrency(5)
    assert settings.get_backup_concurrency() == 5
    for invalid in (0, -1, settings.get_max_backup_concurrency() + 1):
        with pytest.raises(ValueError):
            settings.set_backup_concurrency(invalid)
    assert settings.get_backup_concurrency() == 5


def test_a_lower_maximum_caps_the_setting(monkeypatch):
    settings.set_backup_concurrency(8)
    monkeypatch.setenv("BACKUP_MAX_CONCURRENCY", "3")
    assert settings.get_backup_concurrency() == 3


def test_slots_are_limited_and_given_back():
    settings.set_backup_concurrency(2)
    redis = FakeRedis()
    waited = []

    with backup_limit.slot("a", client=redis), backup_limit.slot("b", client=redis):
        assert backup_limit.running_count(redis) == 2

        # A third backup waits until one finishes.
        def release_after_wait(_):
            waited.append(True)
            redis.members.pop(next(iter(redis.members)))

        with backup_limit.slot("c", client=redis, sleep=release_after_wait):
            assert waited == [True]
    assert backup_limit.running_count(redis) == 0


def test_slot_is_given_back_after_an_error():
    redis = FakeRedis()
    with pytest.raises(RuntimeError):
        with backup_limit.slot("a", client=redis):
            raise RuntimeError("backup failed")
    assert backup_limit.running_count(redis) == 0


def test_change_of_the_limit_applies_to_the_waiting_backup():
    settings.set_backup_concurrency(1)
    redis = FakeRedis()
    with backup_limit.slot("a", client=redis):
        def raise_the_limit(_):
            settings.set_backup_concurrency(2)

        with backup_limit.slot("b", client=redis, sleep=raise_the_limit):
            assert backup_limit.running_count(redis) == 2


def test_stale_slot_of_a_dead_worker_is_released():
    redis = FakeRedis()
    redis.members["dead:1"] = time.time() - backup_limit.STALE_SECONDS - 10
    settings.set_backup_concurrency(1)
    with backup_limit.slot("a", client=redis):
        assert list(redis.members) != ["dead:1"]
