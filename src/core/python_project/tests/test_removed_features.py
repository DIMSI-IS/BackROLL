"""Features that were removed and must not come back as they were.

"Disk Restore To Specified Path" and the listing of the backups of a path took a path from the user and put it in
a shell command (shell=True): any user could run commands on the worker, the second one even a viewer. The task never
worked either: the interface sent the UUID of a machine where it expected the path of a repository.
"""

import importlib

import pytest

pytest.importorskip("libvirt")

from app.initialized import fastapi_app  # noqa: E402


@pytest.fixture(scope="module", autouse=True)
def routes_loaded():
    for name in ("task", "virtual_machine", "job", "restore"):
        try:
            importlib.import_module(f"app.routes.{name}" if name != "restore" else "app.restore")
        except ImportError:
            pass


def paths():
    return {route.path for route in fastapi_app.routes}


def test_no_route_takes_a_path_of_the_server_from_the_user():
    forbidden = [path for path in paths() if "restorespecificpath" in path or "backupsfrompath" in path]
    assert forbidden == []


def test_the_task_that_restored_to_a_path_is_gone():
    from app import restore
    assert not hasattr(restore, "restore_to_path_task")


def test_the_restore_of_a_disk_has_one_way_to_run():
    import inspect
    from app import restore
    source = inspect.getsource(restore.restore_disk_vm)
    assert "mounted" not in source and "restore_to_path" not in source


def test_the_list_of_the_jobs_does_not_offer_it():
    from app.routes import job
    names = [item["name"] for item in job.retrieve_job()]
    assert names == ["Backup (VM)", "Backup (Pool)", "Disk Restore & Replace (VM)"]
    assert all(item["mode"] != "mounted" for item in job.retrieve_job())


def test_no_task_of_the_history_is_the_removed_one():
    from app import task_history
    assert task_history.RESTORE_TASKS == {"VM_Restore_Disk"}
