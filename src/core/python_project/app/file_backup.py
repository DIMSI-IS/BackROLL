"""Backup of folders and files inside the virtual machines.

The chosen paths are read in the disks of a virtual machine with libguestfs, without mounting them,
and sent to Borg as a stream: a tar for a folder, the content for a file. Borg deduplicates them
like the disks, so an unchanged folder costs almost nothing. The archives are named
`files_<path>_<timestamp>`, in the repository of the virtual machine.
"""

import json
import os
import posixpath
import re
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path

from app import archives as archive_groups

ARCHIVE_PREFIX = "files_"
# Ends the name of the stream of a folder, to tell it from a file.
FOLDER_SUFFIX = ".backroll-folder.tar"
MAX_PATHS = 20
MAX_PATH_LENGTH = 4096
HELPER = Path(__file__).with_name("guestfs_helper.py")
# The system Python provides the guestfs module, the virtual environment does not.
SYSTEM_PYTHON = "/usr/bin/python3"


def is_file_archive(archive_name: str) -> bool:
    return archive_name.startswith(ARCHIVE_PREFIX)


def parse_paths(text: str | None) -> list[str]:
    """The paths of a policy are stored one per line."""
    return [line.strip() for line in (text or "").splitlines() if line.strip()]


def validate_paths(paths: list[str]) -> list[str]:
    """Returns the paths in their normal form, or raises ValueError with what is wrong."""
    if len(paths) > MAX_PATHS:
        raise ValueError(f"At most {MAX_PATHS} paths can be backed up.")

    normalized = []
    for path in paths:
        path = path.strip()
        if not path.startswith("/"):
            raise ValueError(f"“{path}” is not an absolute path: it must start with /.")
        # splitlines() cuts at more than \n: a path with one of them would become two paths.
        if "\0" in path or len(path.splitlines()) != 1 or len(path) > MAX_PATH_LENGTH:
            raise ValueError("A path contains an invalid character or is too long.")
        if ".." in path.split("/"):
            raise ValueError(f"“{path}” must not contain “..”.")
        path = posixpath.normpath(path)
        if path == "/":
            raise ValueError("The whole disk is backed up by the normal backup: choose folders.")
        if path not in normalized:
            normalized.append(path)
    return normalized


def archive_slug(path: str) -> str:
    """Letters, digits, dot and dash only: the name is used in a repository and in a URL."""
    return re.sub(r"[^A-Za-z0-9.]+", "-", path.strip("/")).strip("-") or "root"


def archive_names(paths: list[str], timestamp: int) -> dict[str, str]:
    names = {}
    for path in paths:
        slug = archive_slug(path)
        name = f"{ARCHIVE_PREFIX}{slug}_{timestamp}"
        suffix = 2
        # /var/www and /var-www give the same slug.
        while name in names.values():
            name = f"{ARCHIVE_PREFIX}{slug}-{suffix}_{timestamp}"
            suffix += 1
        names[path] = name
    return names


class HelperError(Exception):
    pass


class Helper:
    """The libguestfs helper process, with its JSON lines protocol."""

    def __init__(self, images: list[str]):
        self.process = subprocess.Popen(
            [SYSTEM_PYTHON, str(HELPER)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=True, env={**os.environ, "LIBGUESTFS_BACKEND": "direct"})
        self.request_id = 0
        self.lock = threading.Lock()
        try:
            filesystems = self.call("open", images=images)["filesystems"]
            try:
                self.call("mount")
            except HelperError:
                # No operating system: the first filesystem is used.
                if not filesystems:
                    raise
                self.call("mount", device=filesystems[0]["device"])
        except Exception:
            self.close()
            raise

    def call(self, operation: str, **arguments):
        with self.lock:
            if self.process.poll() is not None:
                raise HelperError("The reader of the disk has stopped.")
            self.request_id += 1
            self.process.stdin.write(json.dumps({"id": self.request_id, "op": operation, **arguments}) + "\n")
            self.process.stdin.flush()
            answer = json.loads(self.process.stdout.readline() or "{}")
        if not answer.get("ok"):
            raise HelperError(answer.get("error") or "The reader of the disk has stopped.")
        return answer["result"]

    def close(self):
        try:
            if self.process.poll() is None:
                try:
                    self.call("close")
                except Exception:
                    pass
                self.process.kill()
        finally:
            self.process.wait()


def run_borg(arguments: list[str], **keywords) -> subprocess.CompletedProcess:
    return subprocess.run(["borg", *arguments], capture_output=True, text=True, **keywords)


def stream_to_borg(helper: Helper, guest_path: str, repository: str, archive: str, stdin_name: str):
    """Reads a path of the disk and stores it as an archive, without any temporary copy."""
    directory = tempfile.mkdtemp(prefix="file-backup-")
    pipe = os.path.join(directory, "stream")
    os.mkfifo(pipe)
    failure = {}

    def read_disk():
        try:
            # Opens the pipe for writing: waits until Borg reads it.
            helper.call("download", path=guest_path, destination=pipe)
        except Exception as exception:
            failure["reader"] = exception
            # Frees Borg, which waits for the end of the stream.
            try:
                open(pipe, "wb").close()
            except OSError:
                pass

    thread = threading.Thread(target=read_disk, daemon=True)
    thread.start()
    try:
        with open(pipe, "rb") as stream:
            result = run_borg(["create", "--stdin-name", stdin_name, f"{repository}::{archive}", "-"],
                              stdin=stream)
        thread.join(timeout=600)
        if "reader" in failure or result.returncode not in (0, 1):
            # A stream that stopped half way must not become a backup that looks complete.
            run_borg(["delete", f"{repository}::{archive}"])
            raise HelperError(str(failure.get("reader") or result.stderr.strip() or "borg failed"))
    finally:
        shutil.rmtree(directory, ignore_errors=True)


def backup_paths(repository: str, images: list[str], paths: list[str], timestamp: int) -> list[dict]:
    """Backs up each path in its own archive. A path that fails does not stop the others."""
    names = archive_names(paths, timestamp)
    helper = Helper(images)
    results = []
    try:
        for path in paths:
            archive = names[path]
            try:
                kind = helper.call("stat", path=path)["type"]
                if kind not in ("directory", "file"):
                    raise HelperError(f"{path} is neither a file nor a folder.")
                # A folder is a tar, a file is its content.
                stdin_name = f"{archive_slug(path)}{FOLDER_SUFFIX}" if kind == "directory" else posixpath.basename(path)
                stream_to_borg(helper, path, repository, archive, stdin_name)
                results.append({"path": path, "archive": archive, "status": "success"})
            except Exception as exception:
                results.append({"path": path, "archive": None, "status": "failed", "error": str(exception)})
    finally:
        helper.close()
    return results


def prune(repository: str, retention: dict):
    """Same retention as the disks, for the archives of files. Each folder is a group apart:
    with one pattern for all of them, one folder of a day would replace the others."""
    keep = [f"--keep-{period}={retention.get(period, 0)}"
            for period in ("daily", "weekly", "monthly", "yearly") if retention.get(period, 0) > 0]
    if not keep:
        return
    listed = run_borg(["list", "--json", "--lock-wait", "30", repository])
    if listed.returncode != 0:
        raise HelperError(listed.stderr.strip() or "borg list failed")
    names = [archive for archive in json.loads(listed.stdout).get("archives", []) if is_file_archive(archive["name"])]
    for group in archive_groups.groups(names):
        result = run_borg(["prune", *keep, "--lock-wait", "30", "--glob-archives", archive_groups.glob_of(group), repository])
        if result.returncode not in (0, 1):
            raise HelperError(result.stderr.strip() or "borg prune failed")
    # Borg frees the space of the deleted backups only with this step. The backup is done: a failure is not one.
    run_borg(["compact", "--lock-wait", "30", repository])
