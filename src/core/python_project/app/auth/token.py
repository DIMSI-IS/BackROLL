from datetime import datetime, timedelta, timezone
from hashlib import sha256

import jwt

from app import settings
from app.environment import MissingEnvironmentVariableException, get_env_var

ALGORITHM = "HS256"
MIN_SECRET_LENGTH = 32


def get_secret() -> str:
    secret = get_env_var("JWT_SECRET")
    if len(secret) < MIN_SECRET_LENGTH:
        raise MissingEnvironmentVariableException(
            f"Variable “JWT_SECRET” must be at least {MIN_SECRET_LENGTH} characters long.")
    return secret


def get_lifetime() -> timedelta:
    return timedelta(minutes=settings.get_value(settings.JWT_LIFETIME_MINUTES))


def check_configuration():
    """Fail fast at startup if the signing secret is missing or too weak."""
    get_secret()
    get_lifetime()


def password_fingerprint(password_hash: bytes) -> str:
    """Changes with the password, so that a password change revokes the issued tokens."""
    return sha256(bytes(password_hash)).hexdigest()[:16]


def create(user) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode({
        "sub": str(user.id),
        "username": user.name,
        "role": user.role,
        "pwd": password_fingerprint(user.password_hash),
        "iat": now,
        "exp": now + get_lifetime(),
    }, get_secret(), algorithm=ALGORITHM)


def decode(token: str) -> dict:
    return jwt.decode(token,
                      get_secret(),
                      algorithms=[ALGORITHM],
                      options={"require": ["sub", "exp", "pwd"]})
