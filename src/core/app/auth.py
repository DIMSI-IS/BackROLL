# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
##
# http://www.apache.org/licenses/LICENSE-2.0
##
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

import os
import json
import requests
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import OAuth2AuthorizationCodeBearer
from starlette.config import Config
from starlette.requests import Request
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse
import jwt
from jwt import PyJWKClient
from pydantic import Json, BaseModel
from authlib.integrations.starlette_client import OAuth

from app import app
from app.patch import make_path

app.add_middleware(SessionMiddleware,
                   secret_key="""zY64v78B#C.-nfp@~zW:*a+mL=xWTKGM""")

config = Config(".env")
oauth = OAuth(config)

issuer_url = os.getenv("OPENID_ISSUER")
metadata_url = make_path(issuer_url, ".well-known/openid-configuration")
connect_url = make_path(issuer_url, "protocol/openid-connect")
auth_url = make_path(connect_url, "auth")
token_url = make_path(connect_url, "token")
certs_url = make_path(connect_url, "certs")

oauth.register(
    name="""openid_provider""",
    client_id=os.getenv("OPENID_CLIENTID"),
    client_secret=os.getenv("OPENID_CLIENTSECRET"),
    server_metadata_url=metadata_url,
    client_kwargs={"scope": "openid email profile"},
)

oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl=auth_url,
    tokenUrl=token_url,
)


class items_login(BaseModel):
    app_id: str
    app_secret: str

    class Config:
        schema_extra = {
            "example": {
                "app_id": "openid application id",
                "app_secret": "openid application secret",
            }
        }


def valid_token(token: str = Security(oauth2_scheme)) -> Json:
    # print(f"Inspect token at https://jwt.io/#id_token={token}.")
    jwks_client = PyJWKClient(certs_url)
    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        # print(f"{signing_key.key=}")
        return jwt.decode(
            token,
            signing_key.key,
            issuer=issuer_url,
            audience="account",
            algorithms=["RS256"],
            options={"verify_aud": False}
        )
    except Exception as exc:
        print(f"{exc=}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),  # "Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


@app.post("/api/v1/login", status_code=200)
def login(item: items_login):
    app_id = item.app_id
    app_secret = item.app_secret
    payload = {
        "grant_type": "client_credentials",
        "client_id": app_id,
        "client_secret": app_secret,
    }
    response = requests.post(token_url, data=payload, timeout=120)
    token = json.loads(response.text)
    return token


@app.post("/api/v1/auth", status_code=200)
def auth(identity: Json = Depends(valid_token)):
    return {"state": "authenticated", "jwt": identity}


@app.get("/api/v1/logout")
def logout(request: Request):
    request.session.pop("user", None)
    return RedirectResponse(url="/")
