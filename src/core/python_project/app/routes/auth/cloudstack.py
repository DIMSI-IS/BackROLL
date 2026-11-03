from fastapi import Depends, HTTPException, Request, status
from pydantic import BaseModel
from app.initialized import fastapi_app
from app import audit, auth
from app.auth import password
from app.routes.auth.password import too_many_attempts


class Credentials(BaseModel):
    app_id: str
    app_secret: str


# The CloudStack plugin authenticates as a regular local user,
# whose role limits what CloudStack can do.
@fastapi_app.post("/api/v1/auth/cloudstack/login")
def login_route(request: Credentials, http_request: Request):
    audit.set_username(http_request, request.app_id)
    try:
        payload = password.login(request.app_id, request.app_secret)
    except password.AccountLocked as locked:
        audit.set_detail(http_request, "account locked")
        raise too_many_attempts(locked)
    if payload is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED,
                            "Invalid credentials.")
    return {"access_token": payload["access_token"]}


@fastapi_app.get("/api/v1/auth/cloudstack/test")
def test_route(identity: dict = Depends(auth.verify_token)):
    return {"username": identity["username"], "role": identity["role"]}
