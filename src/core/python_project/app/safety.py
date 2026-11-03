"""Checks of the values that end in a shell command or in a path.

Many commands of BackROLL are built as text and run by a shell. What an administrator types (the address of a
host, the path of a storage) and what comes in a request (the name of a backup) must therefore be plain values,
checked where they enter, and quoted again where they are used.
"""

import ipaddress
import re

# No leading "-": a name that starts with it would be taken as an option by Borg.
BACKUP_NAME = re.compile(r"^[A-Za-z0-9._][A-Za-z0-9._-]*$")
HOSTNAME = re.compile(r"^(?=.{1,253}$)[A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
                      r"(\.[A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?)*$")
STORAGE_PATH = re.compile(r"^/[A-Za-z0-9._@+=,:/-]*$")
MAX_PATH_LENGTH = 512


def valid_backup_name(name) -> bool:
    return isinstance(name, str) and bool(BACKUP_NAME.match(name)) and name not in (".", "..")


def valid_address(value) -> bool:
    """An IP address (v4 or v6) or a host name."""
    if not isinstance(value, str):
        return False
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return bool(HOSTNAME.match(value))


def valid_storage_path(value) -> bool:
    """An absolute path made of plain characters, without a step back."""
    return (isinstance(value, str) and len(value) <= MAX_PATH_LENGTH and bool(STORAGE_PATH.match(value))
            and ".." not in value.split("/"))
