"""The cleaning of the backup storages. What needs Borg is skipped where it is missing."""

import os
import shutil
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest

os.environ.setdefault("JWT_SECRET", "x" * 40)

from sqlalchemy.pool import StaticPool  # noqa: E402
from sqlmodel import Session, SQLModel, create_engine  # noqa: E402

from app import cleanup  # noqa: E402
from app.database import Storage  # noqa: E402

needs_borg = pytest.mark.skipif(not shutil.which("borg"), reason="borg is required")


@pytest.fixture
def database(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(cleanup, "get_engine", lambda: engine)
    return engine


def test_the_groups_of_archives_of_a_repository_are_found():
    archives = [{"name": "vda_x_1"}, {"name": "vda_x_2"}, {"name": "vdb_y_1"},
                {"name": "files_etc_3"}, {"name": "files_var-www_3"}, {"name": "template"}]
    # One group per disk and one per folder: never one for all the folders.
    assert cleanup.archive_prefixes(archives) == ["files_etc", "files_var-www", "vda_x", "vdb_y"]


@pytest.mark.parametrize("field,expected", [
    ("0", "0"), ("7", "0"), ("1,3,7", "0,1,3"), ("1-7", "0,1,2,3,4,5,6"), ("1-5", "1,2,3,4,5"), ("*", "*"), ("*/2", "*/2")])
def test_the_days_of_the_week_are_written_the_way_celery_counts_them(field, expected):
    assert cleanup.celery_day_of_week(field) == expected


@pytest.mark.parametrize("name", ["../x", "a/b", ".hidden", "template", "restore", "", "a b", "..", "x\n"])
def test_a_repository_name_that_could_leave_the_storage_is_refused(tmp_path, name):
    (tmp_path / "keep").mkdir()
    (tmp_path / "keep" / "config").write_text("[repository]")
    log = cleanup.Log()
    assert cleanup.delete_repository(str(tmp_path), name, log)["deleted"] is False
    assert (tmp_path / "keep" / "config").exists()


def test_a_folder_that_is_not_a_repository_is_not_deleted(tmp_path):
    (tmp_path / "documents").mkdir()
    (tmp_path / "documents" / "a.txt").write_text("precious")
    assert cleanup.delete_repository(str(tmp_path), "documents", cleanup.Log())["deleted"] is False
    assert (tmp_path / "documents" / "a.txt").exists()


def test_a_symbolic_link_is_not_followed(tmp_path):
    target = tmp_path / "elsewhere"
    target.mkdir()
    (target / "config").write_text("[repository]")
    storage = tmp_path / "storage"
    storage.mkdir()
    try:
        os.symlink(target, storage / "linked")
    except OSError:
        pytest.skip("symbolic links are not available")
    assert cleanup.delete_repository(str(storage), "linked", cleanup.Log())["deleted"] is False
    assert (target / "config").exists()


def test_a_repository_in_use_is_skipped(tmp_path):
    repository = tmp_path / "web-01"
    repository.mkdir()
    (repository / "config").write_text("[repository]")
    (repository / "lock.exclusive").mkdir()
    assert cleanup.delete_repository(str(tmp_path), "web-01", cleanup.Log())["deleted"] is False
    assert repository.exists()


def test_the_settings_are_checked_and_saved(database):
    with Session(database) as session:
        storage = Storage(name="backup_storage", path="/mnt/backup_storage")
        session.add(storage)
        session.commit()
        storage_id = storage.id

    default = cleanup.list_settings()[0]
    assert default["keep_days"] == 30 and default["scheduled"] is False

    saved = cleanup.save_settings(storage_id, 14, True, True, "0 3 * * 1", None)
    assert saved["keep_days"] == 14 and saved["schedule"] == "0 3 * * 1"
    assert cleanup.list_settings()[0]["after_backup"] is True

    for keep_days, schedule in ((0, "0 3 * * 1"), (5000, "0 3 * * 1"), (30, "not a cron"), (30, "0 3 * *")):
        with pytest.raises(ValueError):
            cleanup.save_settings(storage_id, keep_days, False, True, schedule, None)
    with pytest.raises(ValueError):
        cleanup.save_settings(storage_id, 30, False, False, "0 3 * * 1", uuid4())
    with pytest.raises(LookupError):
        cleanup.save_settings(uuid4(), 30, False, False, "0 3 * * 1", None)


def test_a_run_is_recorded_with_its_log_and_summary(database):
    with Session(database) as session:
        storage = Storage(name="backup_storage", path="/x")
        session.add(storage)
        session.commit()
        session.refresh(storage)
    run_id = cleanup.create_run(storage, "prune", "manual", "admin")
    assert cleanup.has_running_run(storage.id) is True

    log = cleanup.Log()
    log.add("2 backups deleted")
    cleanup.finish_run(run_id, "success", {"repositories": 1, "archives_deleted": 2, "freed_bytes": 10, "errors": 0}, log)

    run = cleanup.get_run(run_id)
    assert run["status"] == "success" and run["user"] == "admin" and run["trigger"] == "manual"
    assert run["summary"]["archives_deleted"] == 2
    assert "2 backups deleted" in run["log"]
    assert cleanup.has_running_run(storage.id) is False
    assert cleanup.list_runs(10)[0]["id"] == str(run_id)
    assert "log" not in cleanup.list_runs(10)[0]


def make_repository(storage: Path, name: str, archives: dict[str, int]):
    """A repository with archives of one byte, `days_ago` days old: {archive name: days ago}."""
    repository = storage / name
    subprocess.run(["borg", "init", "--encryption", "none", "--make-parent-dirs", str(repository)],
                   check=True, capture_output=True)
    source = storage.parent / "source.txt"
    source.write_text("x")
    for archive, days_ago in archives.items():
        when = (datetime.now() - timedelta(days=days_ago)).replace(microsecond=0).isoformat()
        subprocess.run(["borg", "create", "--timestamp", when, f"{repository}::{archive}", str(source)],
                       check=True, capture_output=True)
    return repository


def archive_names(repository: Path) -> set[str]:
    return {archive["name"] for archive in cleanup.list_archives(repository)}


@needs_borg
def test_old_backups_are_deleted_per_kind_of_archive(tmp_path, monkeypatch):
    monkeypatch.setenv("BORG_UNKNOWN_UNENCRYPTED_REPO_ACCESS_IS_OK", "yes")
    storage = tmp_path / "storage"
    repository = make_repository(storage, "web-01", {
        "vda_x_1": 5, "vda_x_2": 4, "vda_x_3": 3, "vda_x_4": 2, "vda_x_5": 1, "vda_x_6": 0,
        "vdb_y_1": 2, "vdb_y_2": 0,
    })
    log = cleanup.Log()
    result = cleanup.prune_repository(repository, 3, log)

    # Three days of vda are kept, vdb has two days only: nothing to delete there.
    assert archive_names(repository) == {"vda_x_4", "vda_x_5", "vda_x_6", "vdb_y_1", "vdb_y_2"}
    assert result["archives_deleted"] == 3 and result["errors"] == 0
    assert "Pruning archive" in log.text()


@needs_borg
def test_the_days_are_the_days_that_have_a_backup_and_the_oldest_backup_is_not_kept_apart(tmp_path, monkeypatch):
    monkeypatch.setenv("BORG_UNKNOWN_UNENCRYPTED_REPO_ACCESS_IS_OK", "yes")
    storage = tmp_path / "storage"
    # A machine that was backed up on 4 days only, with long gaps between them.
    repository = make_repository(storage, "web-01", {"vda_x_1": 60, "vda_x_2": 30, "vda_x_3": 10, "vda_x_4": 0})

    cleanup.prune_repository(repository, 2, cleanup.Log())

    # The 2 last days with a backup are kept, whatever the gaps: the oldest backups are deleted like the others.
    assert archive_names(repository) == {"vda_x_3", "vda_x_4"}


@needs_borg
def test_the_simulation_says_what_would_be_deleted_and_deletes_nothing(tmp_path, monkeypatch):
    monkeypatch.setenv("BORG_UNKNOWN_UNENCRYPTED_REPO_ACCESS_IS_OK", "yes")
    storage = tmp_path / "storage"
    repository = make_repository(storage, "web-01", {"vda_x_1": 60, "vda_x_2": 30, "vda_x_3": 10, "vda_x_4": 0})
    make_repository(storage, "db-01", {"vda_y_1": 2, "vda_y_2": 0})

    plan = cleanup.plan_storage(str(storage), 2)

    # Only the repository with something to delete is listed, with the backups and their date.
    assert [item["name"] for item in plan["repositories"]] == ["web-01"]
    web = plan["repositories"][0]
    assert [item["name"] for item in web["delete"]] == ["vda_x_1", "vda_x_2"]
    assert web["kept"] == 2 and web["total"] == 4
    assert all(item["time"] and item["group"] == "vda_x" for item in web["delete"])
    assert plan["archives"] == 2 and plan["errors"] == []
    # Nothing was deleted.
    assert archive_names(repository) == {"vda_x_1", "vda_x_2", "vda_x_3", "vda_x_4"}


@needs_borg
def test_only_the_chosen_backups_are_deleted(tmp_path, monkeypatch):
    monkeypatch.setenv("BORG_UNKNOWN_UNENCRYPTED_REPO_ACCESS_IS_OK", "yes")
    storage = tmp_path / "storage"
    repository = make_repository(storage, "web-01", {"vda_x_1": 60, "vda_x_2": 30, "vda_x_3": 10, "vda_x_4": 0})
    log = cleanup.Log()

    # The simulation proposes vda_x_1 and vda_x_2: the administrator keeps vda_x_2.
    summary = cleanup.delete_selected(str(storage), {"web-01": ["vda_x_1"]}, 2, log)

    assert archive_names(repository) == {"vda_x_2", "vda_x_3", "vda_x_4"}
    assert summary["archives_deleted"] == 1 and summary["repositories"] == 1 and summary["errors"] == 0
    assert "vda_x_1 deleted" in log.text()


@needs_borg
def test_a_backup_that_the_rule_keeps_is_never_deleted_even_if_asked(tmp_path, monkeypatch):
    monkeypatch.setenv("BORG_UNKNOWN_UNENCRYPTED_REPO_ACCESS_IS_OK", "yes")
    storage = tmp_path / "storage"
    repository = make_repository(storage, "web-01", {"vda_x_1": 60, "vda_x_2": 30, "vda_x_3": 10, "vda_x_4": 0})
    log = cleanup.Log()

    summary = cleanup.delete_selected(str(storage), {"web-01": ["vda_x_4", "vda_x_3", "not_an_archive_9"]}, 2, log)

    assert archive_names(repository) == {"vda_x_1", "vda_x_2", "vda_x_3", "vda_x_4"}
    assert summary["archives_deleted"] == 0
    assert "vda_x_4 skipped" in log.text()


def test_a_selection_that_could_leave_the_storage_or_hit_a_repository_in_use_is_refused(tmp_path):
    storage = tmp_path / "storage"
    busy = storage / "busy"
    busy.mkdir(parents=True)
    (busy / "config").write_text("[repository]")
    (busy / "lock.exclusive").mkdir()
    log = cleanup.Log()

    summary = cleanup.delete_selected(str(storage), {"../x": ["a_1"], "template": ["a_1"], "busy": ["a_1"],
                                                     "missing": ["a_1"]}, 2, log)

    assert summary == {"repositories": 0, "archives_deleted": 0, "freed_bytes": 0, "errors": 0}
    assert (busy / "config").exists()
    assert "in use" in log.text()


@pytest.mark.parametrize("name,valid", [("vda_x_1", True), ("files_etc-ssh_1792431000", True), ("", False),
                                        ("-delete", False), ("a\nb", False), ("repo::name", False), ("x" * 300, False),
                                        (None, False), (5, False)])
def test_the_names_of_the_chosen_backups_are_checked(name, valid):
    assert cleanup.valid_archive_name(name) is valid


@needs_borg
def test_a_whole_storage_is_cleaned_and_summarized(tmp_path, monkeypatch):
    monkeypatch.setenv("BORG_UNKNOWN_UNENCRYPTED_REPO_ACCESS_IS_OK", "yes")
    storage = tmp_path / "storage"
    make_repository(storage, "web-01", {"vda_x_1": 3, "vda_x_2": 2, "vda_x_3": 1})
    make_repository(storage, "db-01", {"vda_x_1": 2, "vda_x_2": 1})
    # Not repositories: ignored.
    for folder in ("template", "restore", "notes"):
        (storage / folder).mkdir()

    summary = cleanup.prune_storage(str(storage), 2, cleanup.Log())
    assert summary["repositories"] == 2
    assert summary["archives_deleted"] == 1
    assert summary["errors"] == 0
    assert (storage / "notes").exists()


@needs_borg
def test_the_repositories_of_deleted_machines_are_found_and_deleted(tmp_path, monkeypatch):
    monkeypatch.setenv("BORG_UNKNOWN_UNENCRYPTED_REPO_ACCESS_IS_OK", "yes")
    storage = tmp_path / "storage"
    make_repository(storage, "web-01", {"vda_x_1": 1})
    make_repository(storage, "gone-01", {"vda_x_1": 9, "vda_x_2": 8})
    (storage / "template").mkdir()

    orphans = cleanup.find_orphans(str(storage), {"web-01"})
    assert [orphan["name"] for orphan in orphans] == ["gone-01"]
    assert orphans[0]["archives"] == 2 and orphans[0]["size_bytes"] > 0
    assert orphans[0]["last_backup"] is not None

    log = cleanup.Log()
    result = cleanup.delete_repository(str(storage), "gone-01", log)
    assert result["deleted"] is True and result["archives"] == 2
    assert not (storage / "gone-01").exists()
    assert (storage / "web-01" / "config").exists()
    assert "gone-01: deleted" in log.text()


@needs_borg
def test_the_folders_of_a_backup_are_not_deleted_for_each_other(tmp_path, monkeypatch):
    """Both folders are backed up the same day: one retention for all `files_*` would keep one only."""
    monkeypatch.setenv("BORG_UNKNOWN_UNENCRYPTED_REPO_ACCESS_IS_OK", "yes")
    storage = tmp_path / "storage"
    repository = make_repository(storage, "web-01", {
        "files_etc_1000": 0, "files_var-www_1001": 0, "files_etc_900": 1, "files_var-www_901": 1,
        "data_1_x_5": 0, "data_2_x_6": 0,
    })
    cleanup.prune_repository(repository, 30, cleanup.Log())
    assert archive_names(repository) == {"files_etc_1000", "files_var-www_1001", "files_etc_900",
                                         "files_var-www_901", "data_1_x_5", "data_2_x_6"}


@needs_borg
def test_the_repository_is_cleaned_right_after_a_backup_when_the_storage_asks_for_it(database, tmp_path, monkeypatch):
    monkeypatch.setenv("BORG_UNKNOWN_UNENCRYPTED_REPO_ACCESS_IS_OK", "yes")
    storage_path = tmp_path / "storage"
    make_repository(storage_path, "web-01", {"vda_x_1": 5, "vda_x_2": 4, "vda_x_3": 3, "vda_x_4": 2, "vda_x_5": 1})
    with Session(database) as session:
        storage = Storage(name="backup_storage", path=str(storage_path))
        session.add(storage)
        session.commit()
        storage_id = storage.id

    # Not asked: nothing is deleted and nothing is recorded.
    cleanup.after_backup(str(storage_path), "web-01")
    assert len(archive_names(storage_path / "web-01")) == 5
    assert cleanup.list_runs(10) == []

    # Asked: the repository is cleaned and the cleaning is recorded, with its trigger and its log.
    cleanup.save_settings(storage_id, 3, True, False, "0 4 * * 0", None)
    cleanup.after_backup(str(storage_path), "web-01")
    assert len(archive_names(storage_path / "web-01")) == 3
    run = cleanup.list_runs(10)[0]
    assert run["trigger"] == "after_backup" and run["status"] == "success"
    assert run["summary"]["archives_deleted"] == 2

    # A cleaning that deletes nothing is not recorded: the history is not filled by every backup.
    cleanup.after_backup(str(storage_path), "web-01")
    assert len(cleanup.list_runs(10)) == 1


@needs_borg
def test_a_problem_after_a_backup_never_raises(database, tmp_path):
    # Unknown storage, strange name, missing repository: the backup must not fail because of the cleaning.
    cleanup.after_backup(str(tmp_path / "nowhere"), "web-01")
    cleanup.after_backup(str(tmp_path), "../etc")
