from fastapi import Depends, HTTPException, Request

from app import audit, auth, disk_state
from app.initialized import fastapi_app


@fastapi_app.get("/api/v1/attention", status_code=200)
def list_attention(identity: dict = Depends(auth.verify_token)):
    """The machines whose backups are stopped until an administrator has looked at their disks."""
    return disk_state.list_attention()


@fastapi_app.post("/api/v1/attention/{vm_uuid}/resolve", status_code=200)
def resolve_attention(vm_uuid: str, request: Request, disk: str | None = None,
                      identity: dict = Depends(auth.require_admin)):
    """To call once the disks of the machine were checked by hand: the backups of the machine start again."""
    cleared = disk_state.clear(vm_uuid, disk)
    if not cleared:
        raise HTTPException(404, "This machine has nothing waiting for attention.")
    audit.set_detail(request, f"{vm_uuid}{'/' + disk if disk else ''}: {cleared} disk(s) cleared")
    return {"cleared": cleared}
