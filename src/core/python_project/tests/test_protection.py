"""The summary runs everywhere. Reading real repositories needs borg: skipped where it is missing."""

import os
import shutil
import subprocess

import pytest

os.environ.setdefault("JWT_SECRET", "x" * 40)

from app import protection  # noqa: E402


def archive(name, start):
    return {"name": name, "start": start}


def test_files_archives_do_not_count_as_a_backup_of_the_machine():
    summary = protection.summarize([
        archive("vda_x_1", "2026-10-10T10:00:00.000000"),
        archive("files_etc_2", "2026-10-17T10:00:00.000000"),
        archive("vda_x_3", "2026-10-12T10:00:00.000000"),
    ])
    # The same instant, whatever the time zone of the machine that reads it.
    assert protection.parse_time(summary["last_backup"]) == protection.parse_time("2026-10-12T10:00:00.000000")
    assert summary["disk_archives"] == 2
    assert summary["file_archives"] == 1


def test_a_repository_with_only_files_archives_has_no_backup():
    summary = protection.summarize([archive("files_etc_2", "2026-10-17T10:00:00")])
    assert summary["last_backup"] is None


@pytest.mark.skipif(not shutil.which("borg"), reason="borg is required")
def test_repositories_are_read_and_old_ones_are_not_protected(tmp_path, monkeypatch):
    monkeypatch.setenv("BORG_UNKNOWN_UNENCRYPTED_REPO_ACCESS_IS_OK", "yes")
    storage = tmp_path / "storage"
    for folder in ("vm-recent", "vm-empty", "template", "restore", "not-a-repository"):
        (storage / folder).mkdir(parents=True)
    for name in ("vm-recent", "vm-empty", "template"):
        subprocess.run(["borg", "init", "--encryption", "none", str(storage / name)],
                       check=True, capture_output=True)
    source = tmp_path / "data.txt"
    source.write_text("x")
    subprocess.run(["borg", "create", f"{storage / 'vm-recent'}::vda_x_1", str(source)],
                   check=True, capture_output=True)

    protection.clear_cache()
    entries = {entry["name"]: entry for entry in protection.get_protection([str(storage)], 48)}

    # The template folder, the restore folder and a folder that is not a repository are not machines.
    assert set(entries) == {"vm-recent", "vm-empty"}
    assert entries["vm-recent"]["protected"] is True
    assert entries["vm-empty"]["protected"] is False
    assert entries["vm-empty"]["last_backup"] is None

    # Two days and one hour later, the same backup is too old.
    later = protection.time.time() + 49 * 3600
    protection.clear_cache()
    entries = {entry["name"]: entry for entry in protection.get_protection([str(storage)], 48, now=later)}
    assert entries["vm-recent"]["protected"] is False
