from pydantic import Json
from fastapi import Security
import jwt

from app.auth import openid, password


def verify_token(token: str = Security(openid.oauth2_scheme)) -> Json:
    print(f"Inspect token at https://jwt.io/#id_token={token}.")

    if "azp" in jwt.decode(token, options={"verify_signature": False}):
        return openid.verify(token)

    return password.verify(token)
