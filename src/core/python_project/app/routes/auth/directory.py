from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from app import audit, auth
from app.auth import directory
from app.auth.roles import Role
from app.initialized import fastapi_app


class DirectoryUpdate(BaseModel):
    # What is not given is left as it is; the password of the service account too when it is empty or masked.
    enabled: bool | None = None
    server_url: str | None = Field(None, max_length=512)
    start_tls: bool | None = None
    verify_certificate: bool | None = None
    ca_certificate: str | None = Field(None, max_length=20000)
    base_dn: str | None = Field(None, max_length=512)
    bind_dn: str | None = Field(None, max_length=512)
    bind_password: str | None = Field(None, max_length=512)
    user_filter: str | None = Field(None, max_length=1024)
    nested_groups: bool | None = None
    timeout_seconds: int | None = Field(None, ge=2, le=60)


class GroupCreate(BaseModel):
    # The name or the distinguished name of a group of the directory.
    group: str = Field(min_length=1, max_length=512)
    role: Role


class GroupUpdate(BaseModel):
    role: Role


class UserLookup(BaseModel):
    username: str = Field(min_length=1, max_length=256)


def view() -> dict:
    return {"config": directory.public_config(directory.get_config()), "groups": directory.list_groups()}


def changes_of(item: DirectoryUpdate) -> dict:
    return {key: value for key, value in item.model_dump().items() if value is not None}


@fastapi_app.get("/api/v1/directory", status_code=200)
def get_directory(identity: dict = Depends(auth.require_admin)):
    return view()


@fastapi_app.put("/api/v1/directory", status_code=200)
def update_directory(item: DirectoryUpdate, request: Request, identity: dict = Depends(auth.require_admin)):
    changes = changes_of(item)
    before = directory.public_config(directory.get_config())
    try:
        directory.save_config(changes)
    except ValueError as exception:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exception))
    after = directory.public_config(directory.get_config())
    # Never the password, nor the certificate: the names of what changed.
    changed = [key for key in after if before[key] != after[key]]
    if changes.get("bind_password") and directory.MASK not in changes["bind_password"]:
        changed.append("bind password")
    audit.set_detail(request, ", ".join(changed) or "no change")
    return view()


@fastapi_app.post("/api/v1/directory/test", status_code=200)
def test_directory(item: DirectoryUpdate, identity: dict = Depends(auth.require_admin)):
    """Connects with the values of the form (saved or not) and says what went wrong."""
    config = directory.get_config()
    values = directory.merged(config, changes_of(item))
    probe = type(config)(**{**values, "id": 1})
    client = directory.Ldap3Client(probe)
    try:
        directory.check_address(values["server_url"])
        directory.check_config({**values, "enabled": False}, 0)
        client.test()
        return {"ok": True, "message": "The directory answers and the search base exists."}
    except (directory.DirectoryError, ValueError) as error:
        return {"ok": False, "message": str(error)}
    finally:
        client.close()


@fastapi_app.post("/api/v1/directory/lookup", status_code=200)
def lookup_user(item: UserLookup, request: Request, identity: dict = Depends(auth.require_admin)):
    """What a user would get, without his password: where he is found, his groups of the list, his role."""
    audit.set_detail(request, f"username={item.username}")
    config = directory.get_config()
    client = directory.Ldap3Client(config)
    try:
        user = client.find_user(item.username)
        if user is None:
            return {"found": False}
        role, matched = directory.role_of_groups(client, user, directory.list_groups(), bool(config.nested_groups))
        return {"found": True, "dn": user.dn, "username": user.username, "display_name": user.display_name,
                "email": user.email, "disabled": user.disabled, "groups": matched,
                "role": role.value if role else None}
    except directory.DirectoryError as error:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(error))
    finally:
        client.close()


@fastapi_app.post("/api/v1/directory/groups", status_code=201)
def add_group(item: GroupCreate, request: Request, identity: dict = Depends(auth.require_admin)):
    text = item.group.strip()
    group = {"dn": text, "name": text}
    config = directory.get_config()
    if config.server_url and config.base_dn:
        # The directory gives the exact distinguished name, and the name to show.
        client = directory.Ldap3Client(config)
        try:
            found = client.find_group(text)
        except directory.DirectoryError as error:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(error))
        finally:
            client.close()
        if found is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND,
                                "This group was not found in the directory (or several groups have this name: "
                                "give its distinguished name).")
        group = found
    elif "=" not in text:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            "Fill in the connection to the directory first, or give the distinguished name "
                            "of the group (CN=...,DC=...).")
    try:
        created = directory.add_group(group["dn"], group["name"], item.role)
    except ValueError as exception:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exception))
    audit.set_detail(request, f"group={created['name']}, role={item.role.value}")
    return created


@fastapi_app.patch("/api/v1/directory/groups/{group_id}", status_code=200)
def change_group(group_id: UUID, item: GroupUpdate, request: Request, identity: dict = Depends(auth.require_admin)):
    if not directory.change_group_role(group_id, item.role):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Group not found.")
    audit.set_detail(request, f"role={item.role.value}")
    return view()


@fastapi_app.delete("/api/v1/directory/groups/{group_id}", status_code=200)
def remove_group(group_id: UUID, identity: dict = Depends(auth.require_admin)):
    try:
        if not directory.delete_group(group_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Group not found.")
    except ValueError as exception:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exception))
    return view()
