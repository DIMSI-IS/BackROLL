import os
import shutil
from uuid import UUID, uuid4

from celery import chain
from fastapi import Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlmodel import Session, select
from starlette.background import BackgroundTask

from app import audit, auth, file_backup, file_browser
from app.auth.password import get_engine
from app.database import Storage
from app.initialized import celery_app, fastapi_app
from app.routes import host, storage, virtual_machine

MAX_PATH_LENGTH = 4096


def get_storage_paths() -> list[str]:
    with Session(get_engine()) as session:
        return list(session.exec(select(Storage.path)).all())


@celery_app.task(name="Extract a backup to browse its files", bind=True)
def extract_backup_files(self, virtual_machine_list, virtual_machine_id, backup_name, session_id, owner_id):
    virtual_machine = next((x for x in virtual_machine_list
                            if x.get("uuid") == virtual_machine_id), None)
    if not virtual_machine:
        raise ValueError(
            f"virtual machine with id {virtual_machine_id} not found")

    repository = storage.retrieveStoragePathFromHostBackupPolicy(
        virtual_machine)["path"]
    directory = file_browser.get_directory(repository, session_id)
    try:
        if file_backup.is_file_archive(backup_name):
            file_browser.extract_files_archive(
                repository, virtual_machine["name"], backup_name, directory)
        else:
            file_browser.extract_image(
                repository, virtual_machine["name"], backup_name, directory)
        # Written last: its presence means that the content is ready.
        file_browser.write_session_file(
            directory, session_id, owner_id, virtual_machine["name"], backup_name,
            "files" if file_backup.is_file_archive(backup_name) else "disk")
    except Exception:
        shutil.rmtree(directory, ignore_errors=True)
        raise
    return {"session_id": session_id}


@fastapi_app.post("/api/v1/virtualmachines/{virtual_machine_id}/backups/{backup_name}/files", status_code=202)
def open_backup_files(virtual_machine_id: str, backup_name: str,
                      identity: dict = Depends(auth.require_editor)):
    try:
        UUID(virtual_machine_id)
    except ValueError:
        raise HTTPException(404, "Given uuid is not valid")
    if not file_browser.ARCHIVE_NAME_PATTERN.match(backup_name):
        raise HTTPException(422, "Invalid backup name.")

    session_id = str(uuid4())
    task = chain(host.retrieve_host.s(),
                 virtual_machine.dmap.s(virtual_machine.parse_host.s()),
                 virtual_machine.handle_results.s(),
                 extract_backup_files.s(virtual_machine_id, backup_name,
                                        session_id, str(identity["id"]))).apply_async()
    return {"session_id": session_id,
            "Location": fastapi_app.url_path_for("retrieve_task_status", task_id=task.id)}


def find_session(session_id: str, identity: dict):
    try:
        session, status = file_browser.get_session(
            get_storage_paths(), session_id)
    except ValueError:
        raise HTTPException(404, "Session not found.")

    if status == "unknown":
        raise HTTPException(404, "Session not found or expired.")
    if status == "extracting":
        return None
    if session.owner_id != str(identity["id"]) and identity["role"] != "admin":
        raise HTTPException(403, "This session belongs to another user.")
    return session


def get_ready_session(session_id: str, identity: dict):
    session = find_session(session_id, identity)
    if session is None or session.state != "ready":
        raise HTTPException(409, "The disk is not ready yet.")
    return session


@fastapi_app.get("/api/v1/file-browser/{session_id}", status_code=200)
def get_file_browser(session_id: str, identity: dict = Depends(auth.require_editor)):
    session = find_session(session_id, identity)
    if session is None:
        return {"session_id": session_id, "state": "extracting", "error": None, "filesystems": []}
    session.touch()
    return session.to_json()


class FilesystemChoice(BaseModel):
    device: str


@fastapi_app.post("/api/v1/file-browser/{session_id}/filesystem", status_code=200)
def choose_filesystem(session_id: str, item: FilesystemChoice,
                      identity: dict = Depends(auth.require_editor)):
    session = find_session(session_id, identity)
    if session is None or session.state not in ("choose_filesystem", "ready"):
        raise HTTPException(409, "The disk is not ready yet.")
    if item.device not in [fs["device"] for fs in session.filesystems]:
        raise HTTPException(422, "Unknown filesystem.")
    try:
        session.mount(item.device)
    except file_browser.HelperError as exception:
        raise HTTPException(422, str(exception))
    return session.to_json()


def check_path(path: str) -> str:
    if not path.startswith("/") or "\0" in path or len(path) > MAX_PATH_LENGTH:
        raise HTTPException(422, "Invalid path.")
    return path


@fastapi_app.get("/api/v1/file-browser/{session_id}/files", status_code=200)
def list_files(session_id: str, path: str = Query("/"),
               identity: dict = Depends(auth.require_editor)):
    session = get_ready_session(session_id, identity)
    try:
        return {"path": path, "entries": session.call("ls", path=check_path(path))}
    except file_browser.HelperError as exception:
        raise HTTPException(422, str(exception))


@fastapi_app.get("/api/v1/file-browser/{session_id}/download", status_code=200)
def download_file(session_id: str, request: Request, path: str = Query(...),
                  identity: dict = Depends(auth.require_editor)):
    session = get_ready_session(session_id, identity)
    check_path(path)
    audit.set_detail(request, f"path={path}")

    output = session.directory / file_browser.OUTPUT_DIRECTORY / str(uuid4())
    output.parent.mkdir(exist_ok=True)
    try:
        kind = session.call("download", path=path, destination=str(output))["type"]
    except file_browser.HelperError as exception:
        raise HTTPException(422, str(exception))

    name = os.path.basename(path.rstrip("/")) or "disk"
    return FileResponse(
        output, filename=f"{name}.tar" if kind == "directory" else name,
        media_type="application/octet-stream",
        # The copy is deleted once sent.
        background=BackgroundTask(lambda: output.unlink(missing_ok=True)))


@fastapi_app.delete("/api/v1/file-browser/{session_id}", status_code=200)
def close_file_browser(session_id: str, identity: dict = Depends(auth.require_editor)):
    find_session(session_id, identity)
    file_browser.close_session(session_id)
