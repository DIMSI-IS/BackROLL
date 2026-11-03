import json
import re
from ipaddress import IPv4Address
from uuid import UUID

from fastapi import Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field, model_validator
from sqlmodel import Session, select

from app import audit, auth, drp, drp_history, file_backup, file_browser
from app.auth.password import get_engine
from app.borg import borg_core
from app.cloudstack import provisioning
from app.database import ExternalHooks, Storage
from app.initialized import fastapi_app
from app.routes import connectors

CLOUDSTACK_ID = r"^[0-9a-fA-F-]{36}$"
VM_NAME = r"^[A-Za-z0-9][A-Za-z0-9-]{0,62}$"


def get_storage_path(storage_id: UUID) -> str:
    with Session(get_engine()) as session:
        path = session.exec(select(Storage.path).where(Storage.id == storage_id)).first()
    if path is None:
        raise HTTPException(404, "Backup storage not found.")
    return path


def get_connector(connector_id: UUID):
    try:
        return connectors.filter_connector_by_id(str(connector_id))
    except Exception:
        raise HTTPException(404, "Connector not found.")


def list_archives(storage_path: str, repository: str) -> list[dict]:
    try:
        file_browser.check_names(repository, "x")
        archives = json.loads(borg_core.borg_list_backup(
            repository, storage_path)).get("archives", [])
    except ValueError as exception:
        raise HTTPException(422, str(exception))
    except Exception as exception:
        raise HTTPException(500, f"Unable to read the repository. {exception}")
    return sorted(archives, key=lambda archive: archive["start"], reverse=True)


@fastapi_app.get("/api/v1/drp/repositories", status_code=200)
def list_repositories(storage_id: UUID, identity: dict = Depends(auth.require_editor)):
    return {"repositories": drp.list_repositories(get_storage_path(storage_id))}


@fastapi_app.get("/api/v1/drp/repositories/{repository}/archives", status_code=200)
def list_repository_archives(repository: str, storage_id: UUID,
                             identity: dict = Depends(auth.require_editor)):
    archives = list_archives(get_storage_path(storage_id), repository)
    return {"archives": [{
        "name": archive["name"],
        "start": archive["start"],
        # Archives are named after the disk they hold.
        "disk": archive["name"].split("_")[0],
    } for archive in archives if not file_backup.is_file_archive(archive["name"])]}


ACCOUNT_NAME = r"^[A-Za-z0-9._@-]{1,100}$"


@fastapi_app.get("/api/v1/drp/cloudstack/{connector_id}/accounts", status_code=200)
def list_cloudstack_accounts(connector_id: UUID, domain_id: str = Query(..., pattern=CLOUDSTACK_ID),
                             identity: dict = Depends(auth.require_editor)):
    try:
        return {"accounts": provisioning.list_accounts(get_connector(connector_id), domain_id)}
    except provisioning.CloudStackError as exception:
        raise HTTPException(502, str(exception))


@fastapi_app.get("/api/v1/drp/cloudstack/{connector_id}/options", status_code=200)
def get_cloudstack_options(connector_id: UUID,
                           domain_id: str | None = Query(None, pattern=CLOUDSTACK_ID),
                           account: str | None = Query(None, pattern=ACCOUNT_NAME),
                           identity: dict = Depends(auth.require_editor)):
    try:
        options = provisioning.get_options(
            get_connector(connector_id), domain_id, account)
    except provisioning.CloudStackError as exception:
        raise HTTPException(502, str(exception))
    options["mounted_pools"] = drp.get_mounted_pool_ids()
    return options


class DrpRestore(BaseModel):
    storage_id: UUID
    repository: str
    # Backup archives of the disks to restore, the root disk first.
    disks: list[str] = Field(min_length=1, max_length=16)
    connector_id: UUID
    name: str = Field(pattern=VM_NAME)
    zone_id: str = Field(pattern=CLOUDSTACK_ID)
    service_offering_id: str = Field(pattern=CLOUDSTACK_ID)
    template_id: str = Field(pattern=CLOUDSTACK_ID)
    network_id: str | None = Field(None, pattern=CLOUDSTACK_ID)
    ip_address: IPv4Address | None = None
    data_disk_offering_id: str | None = Field(None, pattern=CLOUDSTACK_ID)
    # To create the virtual machine in another domain, for one of its accounts.
    domain_id: str | None = Field(None, pattern=CLOUDSTACK_ID)
    account: str | None = Field(None, pattern=ACCOUNT_NAME)
    # Deletes the new VM, and only it, if the restore fails.
    cleanup_on_failure: bool = False
    # Only shown in the history.
    domain_name: str | None = Field(None, pattern=r"^[A-Za-z0-9 ._/@-]{1,255}$")
    start_after: bool = True
    # The external hook (Slack) told when the restore ends, or fails.
    hook_id: UUID | None = None

    @model_validator(mode="after")
    def check_consistency(self):
        if bool(self.domain_id) != bool(self.account):
            raise ValueError("A domain and an account must be chosen together.")
        if self.ip_address and not self.network_id:
            raise ValueError("An IP address needs a network.")
        if len(self.disks) > 1 and not self.data_disk_offering_id:
            raise ValueError("A disk offering is needed for the data disks.")
        if len(set(self.disks)) != len(self.disks):
            raise ValueError("A disk can not be restored twice.")
        return self


@fastapi_app.post("/api/v1/drp/restore", status_code=202)
def restore_to_new_vm(item: DrpRestore, request: Request,
                      identity: dict = Depends(auth.require_editor)):
    storage_path = get_storage_path(item.storage_id)
    get_connector(item.connector_id)

    existing = {archive["name"]
                for archive in list_archives(storage_path, item.repository)}
    for disk in item.disks:
        if not file_browser.ARCHIVE_NAME_PATTERN.match(disk) or disk not in existing:
            raise HTTPException(422, f"Backup {disk} not found in {item.repository}.")

    target = f", account={item.account} (domain {item.domain_id})" if item.account else ""
    audit.set_detail(request, f"repository={item.repository}, new VM={item.name}, disks={len(item.disks)}{target}")
    drp_request = {
        "storage_path": storage_path,
        "repository": item.repository,
        "disks": item.disks,
        "connector_id": str(item.connector_id),
        "name": item.name,
        "zone_id": item.zone_id,
        "service_offering_id": item.service_offering_id,
        "template_id": item.template_id,
        "network_id": item.network_id,
        "ip_address": str(item.ip_address) if item.ip_address else None,
        "data_disk_offering_id": item.data_disk_offering_id,
        "domain_id": item.domain_id,
        "domain_name": item.domain_name,
        "account": item.account,
        "cleanup_on_failure": item.cleanup_on_failure,
        "start_after": item.start_after,
    }
    connector = get_connector(item.connector_id)
    if item.hook_id:
        with Session(get_engine()) as session:
            if session.get(ExternalHooks, item.hook_id) is None:
                raise HTTPException(422, "The external hook does not exist.")
        drp_request["hook_id"] = str(item.hook_id)
    drp_request["run_id"] = drp_history.create(identity, drp_request, connector.name)
    task = drp.restore_to_new_cloudstack_vm.delay(drp_request)
    drp_history.set_task(drp_request["run_id"], task.id)
    return {"run_id": drp_request["run_id"],
            "Location": fastapi_app.url_path_for("retrieve_task_status", task_id=task.id)}


@fastapi_app.get("/api/v1/drp/history", status_code=200)
def list_drp_history(status: str | None = Query(None, pattern="^(queued|running|success|failed)$"),
                     limit: int = Query(25, ge=1, le=200), offset: int = Query(0, ge=0),
                     identity: dict = Depends(auth.require_editor)):
    return drp_history.list_runs(limit, offset, status)


@fastapi_app.get("/api/v1/drp/history/{run_id}", status_code=200)
def get_drp_run(run_id: UUID, identity: dict = Depends(auth.require_editor)):
    run = drp_history.get_run(str(run_id))
    if run is None:
        raise HTTPException(404, "Restore not found.")
    return run
