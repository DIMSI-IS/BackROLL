from fastapi import Depends
from pydantic import BaseModel, Json
from app.initialized import fastapi_app
from app import auth
from app.auth.password import login


class Credentials(BaseModel):
    app_id: str
    app_secret: str


@fastapi_app.post("/api/v1/auth/cloudstack/login")
def login_route(request: Credentials):
    return {"access_token": login(request.app_id, request.app_secret)}


@fastapi_app.post("/api/v1/auth/cloudstack/test")
def change_route(request: CredentialsChange, identity: Json = Depends(auth.verify_token)):
    pass
