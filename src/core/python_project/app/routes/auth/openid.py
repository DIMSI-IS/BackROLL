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

import json
import requests
from fastapi import Depends
from starlette.requests import Request
from starlette.responses import RedirectResponse
from pydantic import Json, BaseModel

from app.initialized import fastapi_app
from app.auth.openid import token_url, verify


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


@fastapi_app.post("/api/v1/login", status_code=200)
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


@fastapi_app.post("/api/v1/auth", status_code=200)
def auth(identity: Json = Depends(verify)):
    return {"state": "authenticated", "jwt": identity}


@fastapi_app.get("/api/v1/logout")
def logout(request: Request):
    request.session.pop("user", None)
    return RedirectResponse(url="/")
