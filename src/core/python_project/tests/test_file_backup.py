"""The validation of the paths runs everywhere. The backups need borg, qemu-img, mke2fs and libguestfs:
they run in the backend container, and are skipped elsewhere."""

import json
import os
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path

import pytest

os.environ.setdefault("JWT_SECRET", "x" * 40)

from app import file_backup  # noqa: E402

SYSTEM_PYTHON = "/usr/bin/python3"


# Validation

def test_paths_are_normalized_and_deduplicated():
    assert file_backup.validate_paths(["/etc/", "/var//www", "/etc"]) == ["/etc", "/var/www"]


@pytest.mark.parametrize("path", ["etc", "/", "/etc/../root", "/a\nb", "/x" * 3000])
def test_invalid_paths_are_refused(path):
    with pytest.raises(ValueError):
        file_backup.validate_paths([path])


def test_too_many_paths_are_refused():
    with pytest.raises(ValueError):
        file_backup.validate_paths([f"/p{i}" for i in range(file_backup.MAX_PATHS + 1)])


def test_paths_are_stored_one_per_line():
    assert file_backup.parse_paths("/etc\n\n  /var/www \n") == ["/etc", "/var/www"]
    assert file_backup.parse_paths(None) == []


def test_archive_names_are_plain_and_unique():
    names = file_backup.archive_names(["/var/www", "/var-www", "/"], 12)
    assert names["/var/www"] == "files_var-www_12"
    assert names["/var-www"] == "files_var-www-2_12"
    assert all(file_backup.is_file_archive(name) for name in names.values())
    assert not file_backup.is_file_archive("vda_disk_12")


# Backups

def has_guestfs() -> bool:
    if not Path(SYSTEM_PYTHON).exists():
        return False
    return subprocess.run([SYSTEM_PYTHON, "-c", "import guestfs"],
                          capture_output=True).returncode == 0


needs_tools = pytest.mark.skipif(
    not (shutil.which("borg") and shutil.which("qemu-img") and shutil.which("mke2fs") and has_guestfs()),
    reason="borg, qemu-img, mke2fs and libguestfs are required")


def run(*arguments, cwd=None):
    subprocess.run(arguments, cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def disk():
    root = Path(tempfile.mkdtemp())
    source = root / "source"
    (source / "var" / "www").mkdir(parents=True)
    (source / "etc").mkdir()
    (source / "var" / "www" / "index.html").write_text("<h1>hello</h1>")
    (source / "var" / "www" / "big.bin").write_bytes(os.urandom(2_000_000))
    (source / "etc" / "app.conf").write_text("v1\n")
    # A link that leads out of the folder.
    os.symlink("/etc/passwd", source / "var" / "www" / "escape")

    raw = root / "vda.raw"
    run("truncate", "-s", "64M", str(raw))
    run("mke2fs", "-q", "-t", "ext4", "-d", str(source), str(raw))
    image = root / "vda.qcow2"
    run("qemu-img", "convert", "-O", "qcow2", str(raw), str(image))

    # <storage>/<virtual machine>, as BackROLL lays them out.
    repository = root / "storage" / "vm"
    run("borg", "init", "--encryption", "none", "--make-parent-dirs", str(repository))
    yield str(image), str(repository)
    shutil.rmtree(root, ignore_errors=True)


def archives(repository):
    result = subprocess.run(["borg", "list", "--json", repository], capture_output=True, text=True, check=True)
    return [archive["name"] for archive in json.loads(result.stdout)["archives"]]


@needs_tools
def test_folders_and_files_are_backed_up_and_browsed(disk, tmp_path):
    from app import file_browser

    image, repository = disk
    results = file_backup.backup_paths(
        repository, [image], ["/var/www", "/etc/app.conf", "/missing"], 100)
    by_path = {result["path"]: result for result in results}

    assert by_path["/var/www"]["status"] == "success"
    assert by_path["/etc/app.conf"]["status"] == "success"
    assert by_path["/missing"]["status"] == "failed"
    # A failed path leaves nothing that looks like a backup.
    assert sorted(archives(repository)) == ["files_etc-app.conf_100", "files_var-www_100"]

    # The browsing of the folder. extract_files_archive expects the repository of the storage.
    storage = Path(repository).parent
    directory = tmp_path / "extracted"
    file_browser.extract_files_archive(str(storage), "vm", "files_var-www_100", directory)
    session = file_browser.ArchiveSession("id", directory, "owner")

    names = {entry["name"] for entry in session.call("ls", path="/")}
    assert {"index.html", "big.bin"} <= names

    # The link that leads out of the folder is not followed.
    from app.file_browser import HelperError
    with pytest.raises(HelperError):
        session.call("download", path="/escape", destination=str(tmp_path / "leak"))
    with pytest.raises(HelperError):
        session.call("ls", path="/../..")

    out = tmp_path / "index.html"
    assert session.call("download", path="/index.html", destination=str(out))["type"] == "file"
    assert out.read_text() == "<h1>hello</h1>"

    # A file backup is browsed too.
    directory = tmp_path / "extracted-file"
    file_browser.extract_files_archive(str(storage), "vm", "files_etc-app.conf_100", directory)
    session = file_browser.ArchiveSession("id", directory, "owner")
    assert [entry["name"] for entry in session.call("ls", path="/")] == ["app.conf"]


@needs_tools
def test_second_backup_stores_almost_nothing(disk):
    image, repository = disk
    file_backup.backup_paths(repository, [image], ["/var/www"], 100)
    file_backup.backup_paths(repository, [image], ["/var/www"], 200)

    result = subprocess.run(["borg", "info", "--json", f"{repository}::files_var-www_200"],
                            capture_output=True, text=True, check=True)
    stats = json.loads(result.stdout)["archives"][0]["stats"]
    assert stats["original_size"] > 1_500_000
    assert stats["deduplicated_size"] < 100_000


@needs_tools
def test_only_files_archives_are_pruned(disk):
    image, repository = disk
    run("borg", "create", f"{repository}::vda_vda_1", str(image))
    for timestamp in (100, 200, 300):
        file_backup.backup_paths(repository, [image], ["/etc"], timestamp)
    file_backup.prune(repository, {"daily": 1, "weekly": 0, "monthly": 0, "yearly": 0})

    remaining = archives(repository)
    assert "vda_vda_1" in remaining
    assert len([name for name in remaining if file_backup.is_file_archive(name)]) == 1


def test_unsafe_members_of_a_tar_are_skipped(tmp_path):
    from app import file_browser

    source = tmp_path / "source"
    source.mkdir()
    (source / "ok.txt").write_text("ok")
    archive_path = tmp_path / "folder.tar"
    with tarfile.open(archive_path, "w") as archive:
        archive.add(source / "ok.txt", arcname="ok.txt")
        link = tarfile.TarInfo("evil")
        link.type = tarfile.SYMTYPE
        link.linkname = "../../../../etc/passwd"
        archive.addfile(link)
        absolute = tarfile.TarInfo("/tmp/absolute-file")
        archive.addfile(absolute)

    destination = tmp_path / "content"
    destination.mkdir()
    with tarfile.open(archive_path) as archive:
        archive.extractall(destination, filter=file_browser.skip_unsafe_members)
    assert (destination / "ok.txt").read_text() == "ok"
    assert not (destination / "evil").exists()


@needs_tools
def test_the_retention_of_the_folders_is_applied_to_each_folder(disk):
    """Two folders are backed up the same day: the retention keeps the last of each of them."""
    image, repository = disk
    for timestamp in (100, 200):
        file_backup.backup_paths(repository, [image], ["/etc", "/var/www"], timestamp)
    file_backup.prune(repository, {"daily": 1, "weekly": 0, "monthly": 0, "yearly": 0})
    remaining = sorted(name for name in archives(repository) if file_backup.is_file_archive(name))
    assert remaining == ["files_etc_200", "files_var-www_200"]
