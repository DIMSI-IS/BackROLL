"""The names of the machines are put in commands run by a shell: a name with a space, a quote or a semicolon must
stay one argument. Found by the review: the restore ran `rm -rf <folder of the machine>/` without quotes, so a
machine named `web 01` made it delete `web` and `01`, and a name like `*` every folder of the restores."""

import os
import shlex
from types import SimpleNamespace

import pytest

os.environ.setdefault("JWT_SECRET", "x" * 40)

pytest.importorskip("libvirt")

from app.borg import borg_core  # noqa: E402

NAMES = ["web 01", "a;touch x", "$(id)", "*", "it's", "web-01"]


@pytest.fixture
def recorded(monkeypatch):
    commands = []
    monkeypatch.setattr(borg_core.shell, "subprocess_run", lambda command: commands.append(command) or '{"archives": []}')
    monkeypatch.setattr(borg_core.shell, "subprocess_popen", lambda command: commands.append(command) or "")
    return commands


@pytest.mark.parametrize("name", NAMES)
def test_the_repository_of_a_machine_is_created_with_its_name_as_one_argument(tmp_path, recorded, name):
    backup = borg_core.borg_backup({"name": name}, None)
    backup.info["borg_repository"] = str(tmp_path)
    backup.check_repository()
    init = [shlex.split(command) for command in recorded if "borg init" in command]
    assert len(init) == 1
    assert init[0][:4] == ["borg", "init", "--encryption", "none"]
    assert init[0][-1] == f"{tmp_path}/{name}"
    assert len(init[0]) == 5


def test_an_empty_folder_left_by_an_initialization_that_failed_is_initialized_again(tmp_path, recorded):
    (tmp_path / "web-01").mkdir()
    backup = borg_core.borg_backup({"name": "web-01"}, None)
    backup.info["borg_repository"] = str(tmp_path)
    backup.check_repository()
    assert any("borg init" in command for command in recorded)


def test_a_real_repository_is_not_initialized_again(tmp_path, recorded):
    repository = tmp_path / "web-01"
    repository.mkdir()
    (repository / "config").write_text("[repository]")
    backup = borg_core.borg_backup({"name": "web-01"}, None)
    backup.info["borg_repository"] = str(tmp_path)
    backup.check_repository()
    assert not any("borg init" in command for command in recorded)


@pytest.mark.parametrize("name", NAMES)
def test_the_archive_is_created_in_the_repository_of_the_machine_whatever_its_name(tmp_path, recorded, monkeypatch, name):
    backup = borg_core.borg_backup({"name": name}, None)
    backup.info["borg_repository"] = str(tmp_path)
    backup.virtual_machine = {"name": name, "storage": []}
    monkeypatch.setattr(backup, "resolve_disk_source", lambda disk: disk["source"])
    monkeypatch.setattr(backup, "step", lambda *arguments: None)
    backup.create_archive({"device": "vda", "source": "/mnt/pool/My Disk (1).qcow2"})
    words = shlex.split(next(command for command in recorded if "borg create" in command))
    repository, archive = words[-2].split("::")
    assert repository == f"{tmp_path}/{name}"
    # The name of the archive is made of plain characters only: the API accepts nothing else.
    assert all(character.isalnum() or character in "._-" for character in archive)
    assert words[-1] == "/mnt/pool/My Disk (1).qcow2"


@pytest.mark.parametrize("name", NAMES)
def test_the_commands_that_read_a_repository_keep_its_path_as_one_argument(recorded, name):
    borg_core.borg_list_repository(name, "/mnt/backup_storage")
    borg_core.borg_list_backup(name, "/mnt/backup_storage")
    for command in recorded:
        path = [word for word in shlex.split(command) if word.startswith("/mnt/backup_storage")]
        assert path and all(word.split("::")[0] == f"/mnt/backup_storage/{name}" for word in path), command


def test_the_pattern_of_the_archives_is_not_expanded_by_the_shell(monkeypatch, recorded):
    backup = borg_core.borg_backup({"name": "web-01"}, None)
    backup.info["borg_repository"] = "/mnt/backup_storage"
    backup.vm_name = "web-01"
    policy = SimpleNamespace(retention_day=7, retention_week=0, retention_month=0, retention_year=0)
    monkeypatch.setattr(backup, "virtual_machine", {"name": "web-01", "storage": []}, raising=False)
    backup.borg_prune({"device": "vda"}, policy)
    prune = next(command for command in recorded if "borg prune" in command)
    words = shlex.split(prune)
    assert words[words.index("--glob-archives") + 1] == "vda_*"
    # Quoted: the shell gives the pattern to Borg as it is, never the names of the files that match it.
    assert "'vda_*'" in prune or '"vda_*"' in prune


def test_a_retention_that_fails_does_not_fail_the_backup_of_the_disk(monkeypatch):
    """The archive is made: a lock on the repository during the retention must not stop the other disks."""
    commands = []

    def run(command):
        commands.append(command)
        if "borg prune" in command:
            raise borg_core.shell.ShellException(2, "Failed to create/acquire the lock")
        return ""
    monkeypatch.setattr(borg_core.shell, "subprocess_run", run)
    backup = borg_core.borg_backup({"name": "web-01"}, None)
    backup.info["borg_repository"] = "/mnt/backup_storage"
    backup.vm_name = "web-01"
    backup.virtual_machine = {"name": "web-01", "storage": []}
    policy = SimpleNamespace(retention_day=7, retention_week=0, retention_month=0, retention_year=0)

    backup.borg_prune({"device": "vda"}, policy)

    assert any("borg prune" in command for command in commands)
    # Nothing was deleted, so nothing is compacted.
    assert not any("borg compact" in command for command in commands)
