from fastapi import Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, field_validator
from app.initialized import fastapi_app
from app import audit, auth
from app.auth import directory, password
from app.routes.users import USERNAME_PATTERN


class Credentials(BaseModel):
    username: str
    password: str


def too_many_attempts(locked: "password.AccountLocked") -> HTTPException:
    minutes = max(1, -(-locked.retry_after_seconds // 60))
    return HTTPException(
        status.HTTP_429_TOO_MANY_REQUESTS,
        f"Too many failed attempts. Try again in {minutes} minute(s), or ask an administrator to unlock the account.",
        headers={"Retry-After": str(locked.retry_after_seconds)})


@fastapi_app.post("/api/v1/auth/password/login")
def login_route(request: Credentials, http_request: Request):
    audit.set_username(http_request, request.username)
    info: dict = {}
    try:
        payload = password.login(request.username, request.password, info)
    except password.AccountLocked as locked:
        audit.set_detail(http_request, info.get("detail") or "account locked")
        audit.set_source(http_request, info.get("source", "local"))
        raise too_many_attempts(locked)
    except directory.DirectoryError as error:
        audit.set_source(http_request, "ad")
        audit.set_detail(http_request, info.get("detail") or str(error))
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE,
                            "The Active Directory can not be reached. Try again, or use a local account.")
    if info.get("source"):
        audit.set_source(http_request, info["source"])
    if info.get("detail"):
        audit.set_detail(http_request, info["detail"])
    if payload is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED,
                            "Invalid username or password.")
    return payload


@fastapi_app.get("/api/v1/auth/providers")
def providers_route():
    """What the login page may say: whether the users of the Active Directory can log in too."""
    return {"directory": directory.is_enabled()}


@fastapi_app.get("/api/v1/auth/setup")
def setup_status_route():
    return {"required": password.needs_setup()}


class FirstAdmin(BaseModel):
    username: str = Field(pattern=USERNAME_PATTERN)
    password: str

    @field_validator("password")
    @classmethod
    def check_password(cls, value: str):
        return password.validate_password_strength(value)


# Only usable while there is no user. Returns a login payload, as the login route does.
@fastapi_app.post("/api/v1/auth/setup", status_code=201)
def setup_route(request: FirstAdmin, http_request: Request):
    audit.set_username(http_request, request.username)
    payload = password.create_first_admin(request.username, request.password)
    if payload is None:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "The setup is already done.")
    return payload


class PasswordChange(BaseModel):
    old_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def check_new_password(cls, value: str):
        return password.validate_password_strength(value)


@fastapi_app.post("/api/v1/auth/password/change")
def change_route(request: PasswordChange, identity: dict = Depends(auth.verify_token)):
    if identity.get("auth_source") == "ad":
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            "This account belongs to the Active Directory: change its password there.")
    # Changing the password revokes the current token, a new one is returned.
    payload = password.change(
        identity["id"], request.old_password, request.new_password)
    if payload is None:
        # Not a 401: the UI would take it for an expired session.
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            "Wrong current password.")
    return payload


@fastapi_app.get("/api/v1/auth/me")
def me_route(identity: dict = Depends(auth.verify_token)):
    return {"id": str(identity["id"]), "name": identity["username"], "role": identity["role"]}
