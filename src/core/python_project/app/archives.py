"""The names of the Borg archives: `<disk>_<file>_<timestamp>` and `files_<path>_<timestamp>`.

An archive belongs to a group: its name without the timestamp. The backups of one disk, or of one
folder, are a group. A retention is applied to each group apart: when it is applied to a wider set,
one backup of a day replaces the others and whole kinds of backups are deleted.
"""


def group_of(name: str) -> str | None:
    """The name without the trailing timestamp, or None when the name does not end with one."""
    head, separator, tail = name.rpartition("_")
    return head if separator and head and tail.isdigit() else None


def groups(archives: list[dict]) -> list[str]:
    return sorted({group for archive in archives if (group := group_of(archive["name"]))})


def escape_glob(text: str) -> str:
    """Borg patterns are shell globs: the characters that mean something are put between brackets."""
    return "".join(f"[{character}]" if character in "[*?" else character for character in text)


def glob_of(group: str) -> str:
    """The pattern of the archives of a group (the timestamp is a number)."""
    return f"{escape_glob(group)}_[0-9]*"
