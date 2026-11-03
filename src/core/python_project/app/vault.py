"""The secrets that BackROLL keeps in the database and must give back to a service: they are encrypted.

The password of the service account of the Active Directory, the secret key of the CloudStack connectors and the
address of the webhooks (Slack) are encrypted. Encrypted with Fernet (AES, with a signature) by a key made from
SECRETS_KEY, or from JWT_SECRET when SECRETS_KEY is not set. Whoever reads the database, or a backup of it, gets nothing
usable without the key.

Changing the key makes the stored secrets unreadable: they must be typed again (the message says so).
A value without the prefix is a secret stored before the encryption existed: it is read as it is, and encrypted by the
migration of the start (`database.migrate_secrets`) or, at the latest, the next time it is saved.
"""

import base64
import hashlib
import os

from cryptography.fernet import Fernet, InvalidToken

PREFIX = "enc1:"


class SecretError(Exception):
    """The secret can not be read: the key is not the one that encrypted it."""


def key() -> bytes:
    material = os.environ.get("SECRETS_KEY") or os.environ.get("JWT_SECRET") or ""
    if not material:
        raise SecretError("No key to encrypt the secrets: define SECRETS_KEY (or JWT_SECRET).")
    return base64.urlsafe_b64encode(hashlib.sha256(f"backroll-secrets:{material}".encode()).digest())


def is_encrypted(value: str | None) -> bool:
    return bool(value) and value.startswith(PREFIX)


def encrypt(value: str) -> str:
    if not value or is_encrypted(value):
        return value
    return PREFIX + Fernet(key()).encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    if not is_encrypted(value):
        return value or ""
    try:
        return Fernet(key()).decrypt(value[len(PREFIX):].encode()).decode()
    except InvalidToken as error:
        raise SecretError("A stored secret could not be decrypted: the key changed. "
                          "Type it again in the settings.") from error
