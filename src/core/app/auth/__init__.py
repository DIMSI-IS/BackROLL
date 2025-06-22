from pydantic import Json
from fastapi import HTTPException, Security, status
import jwt

from app.auth import openid, password


def verify_token(token: str = Security(openid.oauth2_scheme)) -> Json:
    print(f"Inspect token at https://jwt.io/#id_token={token}.")

    try:
        if "azp" in jwt.decode(token, options={"verify_signature": False}):
            return openid.verify(token)

        return password.verify(token)
    except Exception as exc:
        print(f"{exc=}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),  # "Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
