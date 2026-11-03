"""Needs borg, qemu-img, mke2fs and libguestfs: it runs in the backend container, and is skipped elsewhere."""

import os
import shutil
import subprocess
import tarfile
import tempfile
import time
from pathlib import Path

import pytest

os.environ.setdefault("JWT_SECRET", "x" * 40)

SYSTEM_PYTHON = "/usr/bin/python3"


def has_guestfs() -> bool:
    if not Path(SYSTEM_PYTHON).exists():
        return False
    return subprocess.run([SYSTEM_PYTHON, "-c", "import guestfs"],
                          capture_output=True).returncode == 0


pytestmark = pytest.mark.skipif(
    not (shutil.which("borg") and shutil.which("qemu-img") and shutil.which("mke2fs") and has_guestfs()),
    reason="borg, qemu-img, mke2fs and libguestfs are required")


def run(*arguments, cwd=None):
    subprocess.run(arguments, cwd=cwd, check=True, capture_output=True)


@pytest.fixture(scope="module")
def backup():
    """A Borg repository holding the backup of a small ext4 disk, as BackROLL makes them."""
    from app import file_browser

    root = Path(tempfile.mkdtemp())
    source = root / "source"
    (source / "etc" / "nginx").mkdir(parents=True)
    (source / "home" / "user").mkdir(parents=True)
    (source / "etc" / "nginx" / "nginx.conf").write_text("worker_processes 1;\n")
    (source / "home" / "user" / "notes with spaces.txt").write_text("secret\n")

    disk_directory = root / "disks"
    disk_directory.mkdir()
    raw = disk_directory / "vda.raw"
    run("truncate", "-s", "64M", str(raw))
    run("mke2fs", "-q", "-t", "ext4", "-d", str(source), str(raw))
    run("qemu-img", "convert", "-O", "qcow2", str(raw), str(disk_directory / "vda.qcow2"))
    raw.unlink()

    repository = root / "storage"
    vm_repository = repository / "vm-test"
    run("borg", "init", "--encryption", "none", "--make-parent-dirs", str(vm_repository))
    run("borg", "create", f"{vm_repository}::vda_vda_1", "vda.qcow2", cwd=str(disk_directory))

    yield str(repository), file_browser
    shutil.rmtree(root, ignore_errors=True)


@pytest.fixture(scope="module")
def session(backup):
    repository, file_browser = backup
    session_id = file_browser.new_session_id()
    directory = file_browser.get_directory(repository, session_id)

    file_browser.extract_image(repository, "vm-test", "vda_vda_1", directory)
    file_browser.write_session_file(directory, session_id, "owner", "vm-test", "vda_vda_1")

    found, status = file_browser.get_session([repository], session_id)
    assert status == "found"

    # The first start of libguestfs is slow without hardware acceleration.
    deadline = time.time() + 300
    while found.state == "starting" and time.time() < deadline:
        time.sleep(1)
    if found.state == "choose_filesystem":
        found.mount(found.filesystems[0]["device"])
    assert found.state == "ready", found.error

    yield found
    file_browser.close_session(session_id)
    assert not directory.exists()


def test_filesystems_are_listed(session):
    assert [fs["type"] for fs in session.filesystems] == ["ext4"]


def test_directories_are_listed(session):
    root = session.call("ls", path="/")
    assert {entry["name"] for entry in root} >= {"etc", "home"}
    assert all(entry["type"] == "directory" for entry in root if entry["name"] in ("etc", "home"))

    nginx = session.call("ls", path="/etc/nginx")
    assert [(entry["name"], entry["type"], entry["size"]) for entry in nginx] == [
        ("nginx.conf", "file", len("worker_processes 1;\n"))]


def test_file_with_spaces_can_be_downloaded(session, tmp_path):
    destination = tmp_path / "out"
    result = session.call("download", path="/home/user/notes with spaces.txt",
                          destination=str(destination))
    assert result["type"] == "file"
    assert destination.read_text() == "secret\n"


def test_directory_is_downloaded_as_tar(session, tmp_path):
    destination = tmp_path / "out.tar"
    assert session.call("download", path="/etc", destination=str(destination))["type"] == "directory"
    with tarfile.open(destination) as archive:
        assert any(name.endswith("nginx.conf") for name in archive.getnames())


def test_errors_are_reported(session):
    from app.file_browser import HelperError
    with pytest.raises(HelperError):
        session.call("ls", path="/etc/nginx/nginx.conf")
    with pytest.raises(HelperError):
        session.call("ls", path="/does/not/exist")


def test_names_are_checked(backup):
    _, file_browser = backup
    for bad in ("../x", "a b", "a;b", "", ".."):
        with pytest.raises(ValueError):
            file_browser.check_names("vm", bad)
    file_browser.check_names("vm-test", "vda_vda_1")


# -- the free space: an extraction that would fill the disk is not started -----------------------------------------

def test_the_size_of_an_archive_is_read_from_borg(backup):
    repository, file_browser = backup
    size = file_browser.archive_size(repository, "vm-test", "vda_vda_1")
    # The qcow2 of a 64 MB disk: a few hundred KB to some MB, never zero.
    assert 100 * 1024 < size < 70 * 1024 ** 2


def test_an_extraction_that_would_fill_the_disk_is_refused_before_anything_is_written(backup, tmp_path, monkeypatch):
    repository, file_browser = backup
    free = type("Usage", (), {"total": 48 * 1024 ** 3, "used": 41 * 1024 ** 3, "free": 7 * 1024 ** 3})()
    monkeypatch.setattr(shutil, "disk_usage", lambda path: free)
    # A Windows disk of 12 GB in a disk that has 7 GB free (the case that failed on the lab).
    monkeypatch.setattr(file_browser, "archive_size", lambda *arguments: 12 * 1024 ** 3)

    def forbidden(arguments, cwd=None):
        raise AssertionError(f"nothing must run: {arguments}")
    monkeypatch.setattr(file_browser, "run", forbidden)

    target = tmp_path / "session"
    with pytest.raises(file_browser.NotEnoughSpace, match="Not enough free space.*7.0 GiB is free|only 7.0 GiB"):
        file_browser.extract_image(repository, "vm-test", "vda_vda_1", target)
    assert not target.exists()
    with pytest.raises(file_browser.NotEnoughSpace):
        file_browser.extract_files_archive(repository, "vm-test", "files_etc_1", target)
    assert not target.exists()


def test_a_converted_image_needs_twice_the_room(backup, tmp_path, monkeypatch):
    repository, file_browser = backup
    free = type("Usage", (), {"total": 0, "used": 0, "free": 20 * 1024 ** 3})()
    monkeypatch.setattr(shutil, "disk_usage", lambda path: free)
    monkeypatch.setattr(file_browser, "archive_size", lambda *arguments: 12 * 1024 ** 3)
    monkeypatch.setattr(file_browser, "run", lambda arguments, cwd=None: (_ for _ in ()).throw(AssertionError("no")))
    # 12 GB fit once (13.8 GB with the margin), not twice.
    file_browser.check_free_space(tmp_path, 12 * 1024 ** 3, copies=1)
    with pytest.raises(file_browser.NotEnoughSpace):
        file_browser.check_free_space(tmp_path, 12 * 1024 ** 3, copies=2)


def test_the_message_tells_how_much_is_needed_and_how_much_is_free(backup, tmp_path, monkeypatch):
    repository, file_browser = backup
    monkeypatch.setattr(shutil, "disk_usage", lambda path: type("U", (), {"free": 3 * 1024 ** 3})())
    with pytest.raises(file_browser.NotEnoughSpace) as error:
        file_browser.check_free_space(tmp_path, 10 * 1024 ** 3)
    assert "only 3.0 GiB is free" in str(error.value) and "needs about 12.5 GiB" in str(error.value)
    assert "enlarge the disk" in str(error.value)


def test_a_folder_that_does_not_exist_yet_is_checked_through_its_parent(backup, tmp_path, monkeypatch):
    repository, file_browser = backup
    seen = []
    monkeypatch.setattr(shutil, "disk_usage", lambda path: seen.append(path) or type("U", (), {"free": 10 ** 12})())
    file_browser.check_free_space(tmp_path / "does" / "not" / "exist", 1024)
    assert seen == [tmp_path]
