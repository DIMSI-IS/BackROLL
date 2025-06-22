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

from fastapi import HTTPException, Security, status
from fastapi.security import OAuth2AuthorizationCodeBearer
from starlette.config import Config
from starlette.middleware.sessions import SessionMiddleware
import jwt
from jwt import PyJWKClient
from pydantic import Json
from authlib.integrations.starlette_client import OAuth

from app.initialized import fastapi_app
from app.environment import get_env_var
from app.patch import make_path

fastapi_app.add_middleware(SessionMiddleware,
                           secret_key="""zY64v78B#C.-nfp@~zW:*a+mL=xWTKGM""")

config = Config(".env")
oauth = OAuth(config)

issuer_url = make_path(get_env_var("OPENID_ISSUER"),
                       "realms", get_env_var("OPENID_REALM"))
metadata_url = make_path(issuer_url, ".well-known/openid-configuration")
connect_url = make_path(issuer_url, "protocol/openid-connect")
auth_url = make_path(connect_url, "auth")
token_url = make_path(connect_url, "token")
certs_url = make_path(connect_url, "certs")

oauth.register(
    name="""openid_provider""",
    client_id=get_env_var("OPENID_CLIENT_API_ID"),
    client_secret=get_env_var("OPENID_CLIENT_API_SECRET"),
    server_metadata_url=metadata_url,
    client_kwargs={"scope": "openid email profile"},
)

oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl=auth_url,
    tokenUrl=token_url,
)


def verify(token: str = Security(oauth2_scheme)) -> Json:
    jwks_client = PyJWKClient(certs_url)
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
