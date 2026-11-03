import logging
import secrets

from app.environment import get_env_var

logger = logging.getLogger(__name__)

# HS256 needs a key at least as long as the hash output (32 bytes)
MINIMUM_KEY_LENGTH = 32

__generated_key = None


def get_signing_key() -> str:
    """
    Returns the key used to sign the tokens of the password authentication.

    The key comes from the JWT_SECRET_KEY environment variable.
    When it is not defined, a random key is generated once per process:
    the tokens are then invalid after a restart and users have to log in again.
    """
    global __generated_key

    configured_key = get_env_var(
        "JWT_SECRET_KEY", allow_blank=True, allow_undefined=True)

    if configured_key:
        if len(configured_key) < MINIMUM_KEY_LENGTH:
            logger.warning(
                f"JWT_SECRET_KEY should be at least {MINIMUM_KEY_LENGTH} characters long.")
        return configured_key

    if __generated_key is None:
        logger.warning(
            "JWT_SECRET_KEY is not defined, a random key is used: tokens will be invalid after a restart.")
        __generated_key = secrets.token_urlsafe(48)

    return __generated_key
