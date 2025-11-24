from pydantic import BaseModel
from app.initialized import fastapi_app
from app.auth.password import login, change


class Credentials(BaseModel):
    username: str
    password: str


@fastapi_app.post("/api/v1/auth/password/login")
def login_route(request: Credentials):
    return {"access_token": login(request.username, request.password)}


class CredentialsChange(BaseModel):
    username: str
    old_password: str
    new_password: str


@fastapi_app.post("/api/v1/auth/password/change")
def change_route(request: CredentialsChange):
    change(request.username, request.old_password, request.new_password)
