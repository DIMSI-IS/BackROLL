from uuid import UUID

from fastapi import Depends, Request
from pydantic import BaseModel, Field, field_validator

from app import audit, auth
from app.auth import password, users
from app.auth.roles import Role
from app.initialized import fastapi_app

USERNAME_PATTERN = r"^[A-Za-z0-9._@-]{3,64}$"


class UserCreate(BaseModel):
    name: str = Field(pattern=USERNAME_PATTERN)
    password: str
    role: Role = Role.VIEWER

    @field_validator("password")
    @classmethod
    def check_password(cls, value: str):
        return password.validate_password_strength(value)


class UserUpdate(BaseModel):
    role: Role | None = None
    is_active: bool | None = None
    password: str | None = None
    unlock: bool | None = None

    @field_validator("password")
    @classmethod
    def check_password(cls, value: str | None):
        return value if value is None else password.validate_password_strength(value)


@fastapi_app.get("/api/v1/users", status_code=200)
def list_users(identity: dict = Depends(auth.require_admin)):
    return users.list_users()


@fastapi_app.post("/api/v1/users", status_code=201)
def create_user(item: UserCreate, request: Request, identity: dict = Depends(auth.require_admin)):
    audit.set_detail(request, f"name={item.name}, role={item.role.value}")
    return users.create_user(item.name, item.password, item.role)


@fastapi_app.patch("/api/v1/users/{user_id}", status_code=200)
def update_user(user_id: UUID, item: UserUpdate, request: Request, identity: dict = Depends(auth.require_admin)):
    # Never the password itself.
    changes = []
    if item.role is not None:
        changes.append(f"role={item.role.value}")
    if item.is_active is not None:
        changes.append(f"active={item.is_active}")
    if item.password is not None:
        changes.append("password reset")
    if item.unlock:
        changes.append("unlocked")
    audit.set_detail(request, ", ".join(changes))
    return users.update_user(identity["id"], user_id,
                             item.role, item.is_active, item.password, item.unlock)


@fastapi_app.delete("/api/v1/users/{user_id}", status_code=200)
def delete_user(user_id: UUID, identity: dict = Depends(auth.require_admin)):
    users.delete_user(identity["id"], user_id)
