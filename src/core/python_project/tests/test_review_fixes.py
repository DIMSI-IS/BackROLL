"""Defects found by the independent review of the new modules, each with the scenario that showed it."""

import os
import time

import pytest

os.environ.setdefault("JWT_SECRET", "x" * 40)

from sqlalchemy.pool import StaticPool  # noqa: E402
from sqlmodel import Session, SQLModel, create_engine  # noqa: E402

from app import backup_limit, settings  # noqa: E402


@pytest.fixture
def database(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(settings, "get_engine", lambda: engine)
    return engine


class FakeRedis:
    def __init__(self):
        self.members = {}

    def register_script(self, script):
        def acquire(keys, args):
            now, stale, limit, member = float(args[0]), float(args[1]), int(args[2]), args[3]
            self.members = {m: t for m, t in self.members.items() if t > now - stale}
            if len(self.members) < limit:
                self.members[member] = now
                return 1
            return 0
        return acquire

    def zrem(self, key, member):
        self.members.pop(member, None)


def test_a_backup_without_a_free_place_does_not_wait(database):
    """It goes back to the queue (a retry) instead of sleeping inside the 90 minutes of a backup."""
    settings.set_backup_concurrency(1)
    redis = FakeRedis()
    first = backup_limit.try_acquire("a", client=redis)
    assert first is not None
    started = time.time()
    assert backup_limit.try_acquire("b", client=redis) is None
    assert time.time() - started < 1
    backup_limit.release(first, client=redis)
    assert backup_limit.try_acquire("b", client=redis) is not None
    backup_limit.release(None)  # nothing to give back: no error


def test_the_audit_takes_the_address_added_by_the_proxy():
    from types import SimpleNamespace
    from app import audit
    request = SimpleNamespace(headers={"x-forwarded-for": "6.6.6.6, 203.0.113.9"}, client=SimpleNamespace(host="172.18.0.1"))
    # The first value can be written by the client, the last one is added by nginx.
    assert audit.get_client_ip(request) == "203.0.113.9"
    assert audit.get_client_ip(SimpleNamespace(headers={}, client=SimpleNamespace(host="172.18.0.1"))) == "172.18.0.1"


def test_the_waiting_task_is_shown_as_waiting_and_runs_from_its_real_start(database, monkeypatch):
    from types import SimpleNamespace
    from app import task_history
    monkeypatch.setattr(task_history, "get_engine", settings.get_engine)
    task = SimpleNamespace(name="Single_VM_Backup")
    task_history.on_task_start(task_id="w", task=task, args=[{"name": "web-01"}])
    task_history.on_task_end(task_id="w", task=task, state="RETRY")
    waiting = task_history.list_runs(task_history.BACKUP_TASKS)["w"]
    assert waiting["state"] == "RETRY" and waiting["runtime"] is None
    first_start = waiting["started"]
    time.sleep(0.05)
    task_history.on_task_start(task_id="w", task=task, args=[{"name": "web-01"}])
    task_history.on_task_end(task_id="w", task=task, state="SUCCESS")
    done = task_history.list_runs(task_history.BACKUP_TASKS)["w"]
    assert done["state"] == "SUCCESS" and done["started"] > first_start


def test_a_path_with_a_line_break_of_any_kind_is_refused():
    from app import file_backup
    for text in ("/etc\r/", "/etc\x85/", "/etc\u2028/", "/etc\x0b/", "/etc\x1c/"):
        with pytest.raises(ValueError):
            file_backup.validate_paths([text])
    assert file_backup.validate_paths(["/etc/ssh"]) == ["/etc/ssh"]


def test_a_symbolic_link_is_not_a_repository_of_the_storage(tmp_path):
    from app import protection
    real = tmp_path / "other" / "web-01"
    real.mkdir(parents=True)
    (real / "config").write_text("[repository]")
    storage = tmp_path / "storage"
    storage.mkdir()
    try:
        os.symlink(real, storage / "linked")
    except OSError:
        pytest.skip("symbolic links are not available")
    (storage / "plain").mkdir()
    (storage / "plain" / "config").write_text("[repository]")
    assert [folder.name for folder in protection.find_repositories(str(storage))] == ["plain"]


def test_failed_logins_are_counted_by_the_database(database, monkeypatch):
    """The count is one UPDATE: two requests that arrive together are both counted."""
    from app.auth import password
    from app.database import User
    monkeypatch.setattr(password, "get_engine", lambda: database)
    with Session(database) as session:
        user = User(name="operator", password_hash=password.hash_password("correct horse battery"), role="viewer")
        session.add(user)
        session.commit()
        session.refresh(user)
    monkeypatch.setattr(password, "get_max_failed_attempts", lambda: 5)
    for _ in range(3):
        assert password.login("operator", "wrong password") is None
    with Session(database) as session:
        assert session.get(User, user.id).failed_attempts == 3
    for _ in range(2):
        password.login("operator", "wrong password")
    with Session(database) as session:
        locked = session.get(User, user.id)
        assert locked.failed_attempts == 0 and locked.locked_until is not None
