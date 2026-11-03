from datetime import datetime, timedelta, timezone
from functools import lru_cache
from threading import Lock

import bcrypt
from sqlalchemy import update
from sqlmodel import Session, select, func

from app.auth import token
from app.auth.roles import Role
from app import settings
from app.database import init_db_connection, User
from app.environment import get_env_var

# After that many failed logins in a row, the account is locked for a while: see the settings.


class AccountLocked(Exception):
    def __init__(self, retry_after_seconds: int):
        super().__init__("Account locked.")
        self.retry_after_seconds = retry_after_seconds


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def get_max_failed_attempts() -> int:
    return settings.get_value(settings.LOGIN_MAX_ATTEMPTS)


def get_lock_duration() -> timedelta:
    return timedelta(minutes=settings.get_value(settings.LOGIN_LOCK_MINUTES))


# bcrypt only considers the first 72 bytes.
MAX_PASSWORD_BYTES = 72
MIN_PASSWORD_LENGTH = 8


@lru_cache(maxsize=1)
def get_engine():
    return init_db_connection()


def hash_password(password: str) -> bytes:
    return bcrypt.hashpw(password.encode("utf-8")[:MAX_PASSWORD_BYTES], bcrypt.gensalt())


def check_password(password: str, password_hash: bytes) -> bool:
    return bcrypt.checkpw(password.encode("utf-8")[:MAX_PASSWORD_BYTES], bytes(password_hash))


@lru_cache(maxsize=1)
def get_dummy_hash() -> bytes:
    return hash_password("dummy")


def validate_password_strength(password: str) -> str:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters long.")
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise ValueError(
            f"Password must be at most {MAX_PASSWORD_BYTES} bytes long.")
    return password


def find_user_by_name(session: Session, username: str) -> User | None:
    statement = select(User).where(func.lower(User.name) == username.lower())
    return session.exec(statement).first()


def login_payload(user: User) -> dict:
    return {
        "access_token": token.create(user),
        "token_type": "bearer",
        "expires_in": int(token.get_lifetime().total_seconds()),
        "user": user.to_json(),
    }


def login(username: str, password: str, audit_info: dict | None = None) -> dict | None:
    """Return the login payload, or None for any invalid credentials.

    Raises AccountLocked while the account is locked. The password is not even checked then.
    A user of the Active Directory, or an unknown name while the directory is enabled, is checked by the
    directory (app/auth/directory.py). `audit_info` receives the source and the detail for the audit log.
    """
    from app.auth import directory

    with Session(get_engine()) as session:
        user = find_user_by_name(session, username)

        if (user is not None and user.auth_source == directory.SOURCE) or (user is None and directory.is_enabled()):
            return directory.login(username, password, audit_info)

        if user is None:
            # Spend the same time as for an existing user.
            check_password(password, get_dummy_hash())
            return None

        if user.locked_until is not None:
            locked_until = user.locked_until
            if locked_until.tzinfo is None:
                locked_until = locked_until.replace(tzinfo=timezone.utc)
            remaining = (locked_until - utcnow()).total_seconds()
            if remaining > 0:
                raise AccountLocked(int(remaining) + 1)

        if not check_password(password, user.password_hash) or not user.is_active:
            # The count is increased by the database in one statement: requests that arrive together
            # (bcrypt takes a quarter of a second) must each be counted.
            session.exec(update(User).where(User.id == user.id)
                         .values(failed_attempts=User.failed_attempts + 1))
            session.commit()
            session.refresh(user)
            if user.failed_attempts >= get_max_failed_attempts():
                session.exec(update(User).where(User.id == user.id)
                             .values(locked_until=utcnow() + get_lock_duration(), failed_attempts=0))
                session.commit()
            return None

        if user.failed_attempts or user.locked_until:
            user.failed_attempts = 0
            user.locked_until = None
            session.add(user)
            session.commit()
        return login_payload(user)


def change(user_id, old_password: str, new_password: str) -> dict | None:
    """Change the password and return a new login payload, or None if the old password is wrong."""
    with Session(get_engine()) as session:
        user = session.get(User, user_id)

        if user is None or not check_password(old_password, user.password_hash):
            return None

        user.password_hash = hash_password(new_password)
        session.add(user)
        session.commit()
        session.refresh(user)
        return login_payload(user)


def needs_setup() -> bool:
    """True while there is no user at all: the first admin must then be created."""
    with Session(get_engine()) as session:
        return session.exec(select(func.count()).select_from(User)).one() == 0


__setup_lock = Lock()


def create_first_admin(username: str, password: str) -> dict | None:
    """Create the first admin and return a login payload, or None if a user already exists."""
    with __setup_lock:
        if not needs_setup():
            return None

        with Session(get_engine()) as session:
            user = User(name=username, password_hash=hash_password(password),
                        role=Role.ADMIN.value)
            session.add(user)
            session.commit()
            session.refresh(user)
            return login_payload(user)
