## Licensed to the Apache Software Foundation (ASF) under one
## or more contributor license agreements.  See the NOTICE file
## distributed with this work for additional information
## regarding copyright ownership.  The ASF licenses this file
## to you under the Apache License, Version 2.0 (the
## "License"); you may not use this file except in compliance
## with the License.  You may obtain a copy of the License at
##
##   http://www.apache.org/licenses/LICENSE-2.0
##
## Unless required by applicable law or agreed to in writing,
## software distributed under the License is distributed on an
## "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
## KIND, either express or implied.  See the License for the
## specific language governing permissions and limitations
## under the License.

import os
import json
from fastapi import FastAPI, HTTPException, Security, status
from fastapi.encoders import jsonable_encoder
from starlette.config import Config
from starlette.requests import Request
from starlette.middleware.sessions import SessionMiddleware
import jwt
from jwt import PyJWKClient
from pydantic import Json
from starlette.responses import HTMLResponse, RedirectResponse
from authlib.integrations.starlette_client import OAuth, OAuthError
from fastapi.security import OAuth2AuthorizationCodeBearer

from app import app

app.add_middleware(SessionMiddleware, secret_key="""zY64v78B#C.-nfp@~zW:*a+mL=xWTKGM""")

config = Config('.env')
oauth = OAuth(config)

issuer = os.getenv("OPENID_ISSUER")

CONF_URL = f"""{issuer}/.well-known/openid-configuration"""
oauth.register(
    name="""openid_provider""",
    client_id = os.getenv("OPENID_CLIENTID"),
    client_secret = os.getenv("OPENID_CLIENTSECRET"),
    server_metadata_url=CONF_URL,
    client_kwargs={
        'scope': 'openid email profile'
    }
)

oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl=f"""{issuer}/protocol/openid-connect/auth""",
    tokenUrl=f"""{issuer}/protocol/openid-connect/token"""
)

def valid_token(token: str = Security(oauth2_scheme)) -> Json:
  url = f"""{issuer}/protocol/openid-connect/certs"""
  jwks_client = PyJWKClient(url)
  signing_key = jwks_client.get_signing_key_from_jwt(token)
  try:
    return jwt.decode(
      token, signing_key.key,
      issuer=issuer,
      audience='account',
      algorithms=["RS256"]
    )
  except Exception as e:
    raise HTTPException(
      status_code=status.HTTP_401_UNAUTHORIZED,
      detail=str(e), # "Invalid authentication credentials",
      headers={"WWW-Authenticate": "Bearer"},
    )

@app.get('/login')
async def login(request: Request):
    redirect_uri = request.url_for('auth')
    return await oauth.openid_provider.authorize_redirect(request, redirect_uri)

@app.get('/auth', status_code=200)
async def auth(request: Request):
  try:
      token = await oauth.openid_provider.authorize_access_token(request)
  except OAuthError as error:
      raise HTTPException(status_code=500, detail=jsonable_encoder(error.error))
  user = token.get('userinfo')
  access_token = token.get('access_token')
  return {'state': 'SUCCESS', 'info': { 'access_token': access_token, 'userinfo': user } }

@app.get('/logout')
async def logout(request: Request):
    request.session.pop('user', None)
    return RedirectResponse(url='/')