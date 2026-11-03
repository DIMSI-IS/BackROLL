"""Browse and download the files of a VM backup.

The Borg archive of a disk is extracted once, in a temporary folder next to the
backups. libguestfs then reads the image without mounting it on the host.
The session, with its extracted image, is removed after a period without use.
"""

import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import threading
import time
from logging import Logger
from pathlib import Path
from uuid import UUID, uuid4

from app import file_backup, settings
from app.environment import get_env_var
from app.logging import logged
from app.patch import make_path

BROWSER_DIRECTORY = "restore/.file-browser"
IMAGE_NAME = "disk.img"
SESSION_FILE = "session.json"
OUTPUT_DIRECTORY = "downloads"
CONTENT_DIRECTORY = "content"
# A folder that is being extracted is left alone for this long.
EXTRACTION_GRACE_HOURS = 12
HELPER = Path(__file__).with_name("guestfs_helper.py")
# The system Python provides the guestfs module, the virtual environment does not.
SYSTEM_PYTHON = "/usr/bin/python3"
ARCHIVE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")


def get_ttl_seconds() -> int:
    return settings.get_value(settings.FILE_BROWSER_TTL_MINUTES) * 60


def check_names(vm_name: str, backup_name: str):
    """Names are used in file paths and commands: nothing but plain names is accepted."""
    for name in (vm_name, backup_name):
        if not ARCHIVE_NAME_PATTERN.match(name) or name in (".", ".."):
            raise ValueError(f"Invalid name “{name}”.")


def run(arguments: list[str], cwd: str | None = None) -> str:
    """Runs a command without a shell."""
    result = subprocess.run(arguments, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"{arguments[0]} failed: {result.stderr.strip() or result.stdout.strip()}")
    return result.stdout


# What an extraction needs on top of the size of the archive: the conversions and what the system writes meanwhile.
SPACE_MARGIN = 1.15
SPACE_RESERVE = 1024 ** 3


class NotEnoughSpace(RuntimeError):
    """The disk of BackROLL could not hold the extraction: nothing was started."""


def human(size: float) -> str:
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if size < 1024 or unit == "TiB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024


def archive_size(borg_repository: str, vm_name: str, backup_name: str) -> int:
    """The size of the data of an archive, as borg knows it: what its extraction writes."""
    info = json.loads(run(["borg", "info", "--json", "--lock-wait", "30",
                           f"{make_path(borg_repository, vm_name)}::{backup_name}"]))
    return int(info["archives"][0]["stats"]["original_size"])


def check_free_space(directory: Path, needed: int, copies: int = 1):
    """Refuses to start an extraction that would fill the disk.

    Found on the lab: the extraction of a Windows disk filled the disk of the machine, failed in the middle, and
    left a lock on the repository. `copies` is 2 when the image is converted after its extraction."""
    probe = directory
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    free = shutil.disk_usage(probe).free
    required = needed * copies * SPACE_MARGIN + SPACE_RESERVE
    if free < required:
        raise NotEnoughSpace(
            f"Not enough free space to open this backup: it needs about {human(required)} and only {human(free)} "
            f"is free where BackROLL works ({probe}). Free some space or enlarge the disk, then try again.")


def find_backing_file(borg_repository: str, backing_name: str) -> Path:
    """The backing files of the CloudStack VMs are backed up in the template folder."""
    template = Path(borg_repository) / "template" / backing_name
    # Depending on the version of BackROLL, the file is in a folder of the same name.
    for candidate in (template, template / backing_name):
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        f"The backing file {backing_name} of this disk is not in the template folder of the backup storage.")


def prepare_backing_file(image: Path, borg_repository: str):
    """Points a disk that has a backing file to the saved copy of it. Nothing is written to that copy."""
    info = json.loads(run(["qemu-img", "info", "--output=json", str(image)]))
    backing = info.get("full-backing-filename")
    if not backing:
        return

    template = find_backing_file(borg_repository, os.path.basename(backing))
    template_format = json.loads(
        run(["qemu-img", "info", "--output=json", str(template)]))["format"]
    run(["qemu-img", "rebase", "-u", "-f", info["format"],
         "-F", template_format, "-b", str(template), str(image)])


def extract_image(borg_repository: str, vm_name: str, backup_name: str, directory: Path, copies: int = 1) -> Path:
    check_names(vm_name, backup_name)
    check_free_space(directory, archive_size(borg_repository, vm_name, backup_name), copies)
    directory.mkdir(parents=True, exist_ok=True)

    # The extended attributes and ACLs are useless to read a disk image,
    # and not every storage supports them.
    run(["borg", "extract", "--sparse", "--noxattrs", "--noacls",
         f"{make_path(borg_repository, vm_name)}::{backup_name}"], cwd=str(directory))

    files = [path for path in directory.rglob("*") if path.is_file()]
    if not files:
        raise RuntimeError("The backup does not contain any disk file.")
    disk = max(files, key=lambda path: path.stat().st_size)
    image = directory / IMAGE_NAME
    disk.rename(image)
    # Leftover folders of the archive.
    for folder in [path for path in directory.iterdir() if path.is_dir()]:
        shutil.rmtree(folder, ignore_errors=True)

    prepare_backing_file(image, borg_repository)
    return image


def skip_unsafe_members(member: tarfile.TarInfo, destination: str):
    """The tar comes from a virtual machine: what could escape the folder is left out."""
    try:
        return tarfile.data_filter(member, destination)
    except tarfile.FilterError:
        return None


def extract_files_archive(borg_repository: str, vm_name: str, backup_name: str, directory: Path) -> Path:
    """Extracts an archive made by the backup of folders and files. Returns the folder to browse."""
    check_names(vm_name, backup_name)
    check_free_space(directory, archive_size(borg_repository, vm_name, backup_name), 2)
    raw = directory / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    run(["borg", "extract", "--noxattrs", "--noacls",
         f"{make_path(borg_repository, vm_name)}::{backup_name}"], cwd=str(raw))

    files = [path for path in raw.rglob("*") if path.is_file()]
    if len(files) != 1:
        raise RuntimeError("This backup of folders and files is not readable.")
    source = files[0]

    content = directory / CONTENT_DIRECTORY
    content.mkdir()
    if source.name.endswith(file_backup.FOLDER_SUFFIX):
        with tarfile.open(source) as archive:
            archive.extractall(content, filter=skip_unsafe_members)
    else:
        source.rename(content / source.name)
    shutil.rmtree(raw, ignore_errors=True)
    return content


def write_session_file(directory: Path, session_id: str, owner_id: str, vm_name: str, backup_name: str,
                       kind: str = "disk"):
    (directory / SESSION_FILE).write_text(json.dumps({
        "session_id": session_id,
        "owner_id": owner_id,
        "vm": vm_name,
        "backup": backup_name,
        "kind": kind,
    }))


class HelperError(Exception):
    pass


class BrowserSession:
    """A libguestfs helper process reading one extracted disk image."""

    def __init__(self, session_id: str, directory: Path, owner_id: str):
        self.session_id = session_id
        self.directory = directory
        self.owner_id = owner_id
        self.state = "starting"
        self.error: str | None = None
        self.filesystems: list[dict] = []
        self.last_used = time.time()
        self.lock = threading.Lock()
        self.request_id = 0
        self.process: subprocess.Popen | None = None
        threading.Thread(target=self.start, daemon=True).start()

    def start(self):
        try:
            log = open(self.directory / "helper.log", "w")
            self.process = subprocess.Popen(
                [SYSTEM_PYTHON, str(HELPER)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=log, text=True,
                env={**os.environ, "LIBGUESTFS_BACKEND": "direct"})
            result = self.call("open", image=str(self.directory / IMAGE_NAME))
            self.filesystems = result["filesystems"]
            try:
                self.call("mount")
                self.state = "ready"
            except HelperError as exception:
                # Not an operating system: the user chooses the filesystem to read.
                self.error = str(exception)
                self.state = "choose_filesystem"
        except Exception as exception:
            self.error = str(exception)
            self.state = "error"

    def call(self, operation: str, **arguments):
        with self.lock:
            if self.process is None or self.process.poll() is not None:
                raise HelperError("The reader of the disk has stopped.")
            self.request_id += 1
            request = {"id": self.request_id, "op": operation, **arguments}
            self.process.stdin.write(json.dumps(request) + "\n")
            self.process.stdin.flush()
            answer = json.loads(self.process.stdout.readline() or "{}")
        self.touch()
        if not answer.get("ok"):
            raise HelperError(answer.get("error") or "The reader of the disk has stopped.")
        return answer["result"]

    def touch(self):
        self.last_used = time.time()
        try:
            os.utime(self.directory)
        except OSError:
            pass

    def mount(self, device: str):
        self.call("mount", device=device)
        self.error = None
        self.state = "ready"

    def to_json(self) -> dict:
        return {
            "session_id": self.session_id,
            "state": self.state,
            "error": self.error,
            "filesystems": self.filesystems,
        }

    def close(self):
        try:
            if self.process and self.process.poll() is None:
                try:
                    self.call("close")
                except Exception:
                    pass
                self.process.kill()
        finally:
            shutil.rmtree(self.directory, ignore_errors=True)


class ArchiveSession(BrowserSession):
    """The extracted folders and files of a backup. It answers like the libguestfs helper does."""

    def __init__(self, session_id: str, directory: Path, owner_id: str):
        self.session_id = session_id
        self.directory = directory
        self.owner_id = owner_id
        self.state = "ready"
        self.error = None
        self.filesystems = []
        self.last_used = time.time()
        self.process = None

    def resolve(self, path: str) -> Path:
        root = (self.directory / CONTENT_DIRECTORY).resolve()
        target = (root / path.lstrip("/")).resolve()
        # A link of the backup must not lead out of it.
        if target != root and root not in target.parents:
            raise HelperError("Not found.")
        return target

    def call(self, operation: str, **arguments):
        self.touch()
        if operation == "ls":
            target = self.resolve(arguments["path"])
            if not target.is_dir():
                raise HelperError("Not a directory.")
            entries = []
            for child in target.iterdir():
                info = child.lstat()
                mode = info.st_mode
                kind = ("directory" if stat.S_ISDIR(mode) else "link" if stat.S_ISLNK(mode)
                        else "file" if stat.S_ISREG(mode) else "other")
                entries.append({"name": child.name, "type": kind, "size": info.st_size,
                                "mode": oct(stat.S_IMODE(mode)), "modified": int(info.st_mtime)})
            entries.sort(key=lambda entry: (entry["type"] != "directory", entry["name"].lower()))
            return entries
        if operation == "download":
            target = self.resolve(arguments["path"])
            if target.is_dir():
                with tarfile.open(arguments["destination"], "w") as archive:
                    archive.add(target, arcname=target.name or "files")
                return {"type": "directory"}
            if not target.is_file():
                raise HelperError("Not found.")
            shutil.copyfile(target, arguments["destination"])
            return {"type": "file"}
        raise HelperError("Not available for this backup.")

    def mount(self, device: str):
        raise HelperError("Not available for this backup.")


sessions: dict[str, BrowserSession] = {}
sessions_lock = threading.Lock()


def get_directory(borg_repository: str, session_id: str) -> Path:
    # The identifier is built from a UUID: no path can be injected.
    return Path(borg_repository) / BROWSER_DIRECTORY / str(UUID(session_id))


def new_session_id() -> str:
    return str(uuid4())


def get_session(storage_paths: list[str], session_id: str) -> tuple[BrowserSession | None, str]:
    """Returns the session (started if needed) and its status: "extracting", "unknown" or "found"."""
    UUID(session_id)
    with sessions_lock:
        session = sessions.get(session_id)
        if session:
            return session, "found"

        for storage_path in storage_paths:
            directory = get_directory(storage_path, session_id)
            session_file = directory / SESSION_FILE
            if session_file.is_file():
                details = json.loads(session_file.read_text())
                session_class = ArchiveSession if details.get("kind") == "files" else BrowserSession
                session = session_class(session_id, directory, details["owner_id"])
                sessions[session_id] = session
                return session, "found"
            if directory.is_dir():
                return None, "extracting"
    return None, "unknown"


def close_session(session_id: str):
    with sessions_lock:
        session = sessions.pop(session_id, None)
    if session:
        session.close()


def remove_stale(storage_paths: list[str]):
    """Closes the sessions that are not used any more and removes orphan folders."""
    limit = time.time() - get_ttl_seconds()

    with sessions_lock:
        stale = [identifier for identifier, session in sessions.items()
                 if session.last_used < limit]
    for identifier in stale:
        close_session(identifier)

    for storage_path in storage_paths:
        root = Path(storage_path) / BROWSER_DIRECTORY
        if not root.is_dir():
            continue
        for directory in root.iterdir():
            try:
                if directory.name in sessions:
                    continue
                # A folder without session file is being extracted: the extraction of a large disk
                # takes longer than the life of a session. Only a very old one is abandoned.
                extracting = not (directory / SESSION_FILE).is_file()
                age_limit = time.time() - (EXTRACTION_GRACE_HOURS * 3600 if extracting else get_ttl_seconds())
                if directory.stat().st_mtime < age_limit:
                    shutil.rmtree(directory, ignore_errors=True)
            except OSError:
                pass


@logged(bounds=False)
def start_cleaner(get_storage_paths, logger: Logger):
    def loop():
        while True:
            time.sleep(60)
            try:
                remove_stale(get_storage_paths())
            except Exception as exception:
                logger.error(f"Unable to clean the file browser sessions. {exception}")

    threading.Thread(target=loop, daemon=True).start()
