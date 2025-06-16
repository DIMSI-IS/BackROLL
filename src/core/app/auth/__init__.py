from pydantic import Json
from fastapi import Security
import jwt

from app.auth import openid, password


def valid_token(token: str = Security(openid.oauth2_scheme)) -> Json:
    print(f"Inspect token at https://jwt.io/#id_token={token}.")

    if "azp" in jwt.decode(token, options={"verify_signature": False}):
        return openid.valid_token(token)

    return password.verify(token)
