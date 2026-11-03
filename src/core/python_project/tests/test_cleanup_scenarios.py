"""The cleaning of the storages, in the cases that a real storage meets: odd names, empty repositories, a backup
made between the simulation and the deletion. With the real Borg."""

import os
import shutil

import pytest

os.environ.setdefault("JWT_SECRET", "x" * 40)

from app import cleanup  # noqa: E402
from test_cleanup import archive_names, make_repository  # noqa: E402

needs_borg = pytest.mark.skipif(not shutil.which("borg"), reason="borg is required")


@pytest.fixture(autouse=True)
def borg_environment(monkeypatch):
    monkeypatch.setenv("BORG_UNKNOWN_UNENCRYPTED_REPO_ACCESS_IS_OK", "yes")


@needs_borg
def test_a_repository_without_any_backup_is_simulated_and_cleaned_without_error(tmp_path):
    repository = make_repository(tmp_path / "storage", "empty-vm", {})
    plan = cleanup.plan_repository(repository, 3)
    assert plan["total"] == 0 and plan["delete"] == [] and plan["kept"] == 0
    summary = cleanup.delete_selected(str(tmp_path / "storage"), {"empty-vm": []}, 3, cleanup.Log())
    assert summary["errors"] == 0 and summary["archives_deleted"] == 0
    result = cleanup.prune_repository(repository, 3, cleanup.Log())
    assert result["errors"] == 0


@needs_borg
def test_an_archive_that_does_not_end_with_a_timestamp_is_never_proposed_nor_deleted(tmp_path):
    storage = tmp_path / "storage"
    repository = make_repository(storage, "web-01", {"vda_x_1": 60, "vda_x_2": 30, "vda_x_3": 0, "manual-copy": 90})
    plan = cleanup.plan_repository(repository, 1)
    assert "manual-copy" not in [item["name"] for item in plan["delete"]]
    cleanup.delete_selected(str(storage), {"web-01": ["manual-copy", "vda_x_1"]}, 1, cleanup.Log())
    # The backup that a person made by hand stays, the one of the rule goes.
    assert "manual-copy" in archive_names(repository) and "vda_x_1" not in archive_names(repository)


@needs_borg
def test_names_with_spaces_and_accents_are_simulated_and_deleted_as_one_name(tmp_path):
    storage = tmp_path / "storage"
    repository = make_repository(storage, "web-01", {"files_Mes documents_1": 60, "files_Mes documents_2": 30,
                                                     "files_Mes documents_3": 0, "files_café_1": 50, "files_café_2": 0})
    plan = cleanup.plan_repository(repository, 1)
    proposed = {item["name"] for item in plan["delete"]}
    assert proposed == {"files_Mes documents_1", "files_Mes documents_2", "files_café_1"}
    summary = cleanup.delete_selected(str(storage), {"web-01": sorted(proposed)}, 1, cleanup.Log())
    assert summary["archives_deleted"] == 3 and summary["errors"] == 0
    assert archive_names(repository) == {"files_Mes documents_3", "files_café_2"}


@needs_borg
def test_a_pattern_character_in_a_name_does_not_touch_the_other_groups(tmp_path):
    """`[` and `*` mean something to Borg: the retention of one group must not reach another."""
    storage = tmp_path / "storage"
    repository = make_repository(storage, "web-01", {"files_a[b]_1": 60, "files_a[b]_2": 0,
                                                     "files_aXb_1": 60, "files_aXb_2": 0})
    plan = cleanup.plan_repository(repository, 1)
    assert {item["name"] for item in plan["delete"]} == {"files_a[b]_1", "files_aXb_1"}


@needs_borg
def test_a_backup_made_between_the_simulation_and_the_deletion_is_kept_and_does_not_block_the_rest(tmp_path):
    storage = tmp_path / "storage"
    repository = make_repository(storage, "web-01", {"vda_x_1": 60, "vda_x_2": 30, "vda_x_3": 0})
    proposed = [item["name"] for item in cleanup.plan_repository(repository, 2)["delete"]]
    assert proposed == ["vda_x_1"]

    # A backup runs now: the newest one of the day.
    # Same clock as the helper that made the others (it uses the local time), a few seconds later.
    source = storage.parent / "source.txt"
    import subprocess
    from datetime import datetime, timedelta
    later = (datetime.now() + timedelta(seconds=10)).replace(microsecond=0).isoformat()
    subprocess.run(["borg", "create", "--timestamp", later, f"{repository}::vda_x_4", str(source)],
                   check=True, capture_output=True)

    summary = cleanup.delete_selected(str(storage), {"web-01": proposed + ["vda_x_4"]}, 2, cleanup.Log())
    # The old one is deleted, the new one is not (the rule keeps it), nothing fails.
    assert summary["errors"] == 0
    assert "vda_x_1" not in archive_names(repository) and "vda_x_4" in archive_names(repository)


@needs_borg
def test_the_same_selection_sent_twice_deletes_once_and_fails_nowhere(tmp_path):
    storage = tmp_path / "storage"
    repository = make_repository(storage, "web-01", {"vda_x_1": 60, "vda_x_2": 30, "vda_x_3": 0})
    first = cleanup.delete_selected(str(storage), {"web-01": ["vda_x_1"]}, 2, cleanup.Log())
    second = cleanup.delete_selected(str(storage), {"web-01": ["vda_x_1"]}, 2, cleanup.Log())
    assert first["archives_deleted"] == 1 and second["archives_deleted"] == 0 and second["errors"] == 0
    assert archive_names(repository) == {"vda_x_2", "vda_x_3"}


@needs_borg
def test_a_repository_that_is_damaged_is_reported_and_the_others_are_still_simulated(tmp_path):
    storage = tmp_path / "storage"
    make_repository(storage, "good-01", {"vda_x_1": 60, "vda_x_2": 0})
    broken = make_repository(storage, "broken-01", {"vda_x_1": 60, "vda_x_2": 0})
    # The configuration is there (it looks like a repository) but the data is gone.
    shutil.rmtree(broken / "data")
    plan = cleanup.plan_storage(str(storage), 1)
    assert [item["name"] for item in plan["repositories"]] == ["good-01"]
    assert [item["name"] for item in plan["errors"]] == ["broken-01"] and plan["errors"][0]["error"]


@needs_borg
def test_one_repository_that_fails_does_not_stop_the_cleaning_of_the_others(tmp_path):
    storage = tmp_path / "storage"
    make_repository(storage, "a-good", {"vda_x_1": 60, "vda_x_2": 0})
    broken = make_repository(storage, "b-broken", {"vda_x_1": 60, "vda_x_2": 0})
    shutil.rmtree(broken / "data")
    make_repository(storage, "c-good", {"vda_x_1": 60, "vda_x_2": 0})
    log = cleanup.Log()
    summary = cleanup.prune_storage(str(storage), 1, log)
    assert summary["repositories"] == 3 and summary["errors"] == 1 and summary["archives_deleted"] == 2
