from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from app.auth import token
from app.auth.password import get_engine
from app.auth.roles import Role
from app.database import User

bearer_scheme = HTTPBearer(auto_error=False)


def unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def verify_token(request: Request,
                credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme)) -> dict:
    """Authenticate the request. Any active user passes: it is the viewer level.

    The user is read from the database at each request, so that role changes,
    deactivations and password changes apply immediately.
    """
    if credentials is None:
        raise unauthorized()

    try:
        claims = token.decode(credentials.credentials)
        user_id = UUID(claims["sub"])
    except (jwt.PyJWTError, ValueError) as exception:
        raise unauthorized() from exception

    with Session(get_engine()) as session:
        user = session.get(User, user_id)

    if user is None or not user.is_active \
            or claims["pwd"] != token.password_fingerprint(user.password_hash):
        raise unauthorized()

    identity = {"id": user.id, "username": user.name, "role": user.role,
                "auth_source": user.auth_source or "local"}
    # Read by the audit log.
    request.state.identity = identity
    return identity


def require_role(minimum: Role):
    def dependency(identity: dict = Depends(verify_token)) -> dict:
        if Role(identity["role"]).rank < minimum.rank:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"The “{minimum.value}” role is required.",
            )
        return identity
    return dependency


require_viewer = verify_token
require_editor = require_role(Role.EDITOR)
require_admin = require_role(Role.ADMIN)
