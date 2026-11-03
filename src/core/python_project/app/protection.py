"""Which virtual machines are protected: the date of the last backup in each Borg repository.

A repository is the folder of a virtual machine in a backup storage. The archives of folders and files
do not count as a backup of the machine: only the archives of its disks do.
"""

import json
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from app import file_backup

IGNORED_FOLDERS = {"template", "restore"}
CACHE_SECONDS = 60
LOCK_WAIT_SECONDS = 5

_cache: dict[tuple, tuple[float, list[dict]]] = {}
_cache_lock = threading.Lock()


def find_repositories(storage_path: str) -> list[Path]:
    root = Path(storage_path)
    if not root.is_dir():
        return []
    return sorted(folder for folder in root.iterdir()
                  if folder.is_dir() and not folder.is_symlink() and folder.name not in IGNORED_FOLDERS
                  and not folder.name.startswith(".") and (folder / "config").is_file())


def parse_time(text: str) -> datetime:
    """Borg gives the start of an archive in local time, without a time zone."""
    parsed = datetime.fromisoformat(text)
    return parsed.astimezone(timezone.utc) if parsed.tzinfo is None else parsed


def summarize(archives: list[dict]) -> dict:
    """From the archives of a repository, as `borg list --json` gives them."""
    disks = [archive for archive in archives if not file_backup.is_file_archive(archive["name"])]
    last = max((parse_time(archive["start"]) for archive in disks), default=None)
    return {
        "last_backup": last.isoformat() if last else None,
        "disk_archives": len(disks),
        "file_archives": len(archives) - len(disks),
    }


def read_repository(repository: Path) -> dict:
    name = repository.name
    result = subprocess.run(
        ["borg", "list", "--json", "--lock-wait", str(LOCK_WAIT_SECONDS), str(repository)],
        capture_output=True, text=True)
    if result.returncode != 0:
        locked = "lock" in result.stderr.lower()
        return {"name": name, "state": "locked" if locked else "unreadable",
                "last_backup": None, "disk_archives": 0, "file_archives": 0}
    summary = summarize(json.loads(result.stdout).get("archives", []))
    return {"name": name, "state": "ok", **summary}


def get_protection(storage_paths: list[str], max_age_hours: int = 48, now: float | None = None) -> list[dict]:
    """One entry per repository, with `protected` false when the last backup is older than the limit.

    The answer is kept for a minute: every open dashboard asks for it.
    """
    now = now if now is not None else time.time()
    key = tuple(sorted(storage_paths))
    with _cache_lock:
        cached = _cache.get(key)
        if cached and now - cached[0] < CACHE_SECONDS:
            entries = cached[1]
        else:
            entries = []
            for storage_path in storage_paths:
                for repository in find_repositories(storage_path):
                    entries.append({"storage": storage_path, **read_repository(repository)})
            _cache[key] = (now, entries)

    limit = now - max_age_hours * 3600
    return [{**entry,
             "protected": bool(entry["last_backup"]) and parse_time(entry["last_backup"]).timestamp() >= limit}
            for entry in entries]


def clear_cache():
    with _cache_lock:
        _cache.clear()
