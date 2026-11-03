from uuid import UUID

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.auth.password import find_user_by_name, get_engine, hash_password
from app.auth.roles import Role
from app.database import User


def get_or_404(session: Session, user_id: UUID) -> User:
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found.")
    return user


def list_users() -> list[dict]:
    with Session(get_engine()) as session:
        users = session.exec(select(User).order_by(User.name)).all()
        return [user.to_json() for user in users]


def create_user(name: str, password: str, role: Role) -> dict:
    with Session(get_engine()) as session:
        if find_user_by_name(session, name) is not None:
            raise HTTPException(status.HTTP_409_CONFLICT,
                                "This username is already used.")

        user = User(name=name, password_hash=hash_password(
            password), role=role.value)
        session.add(user)
        session.commit()
        session.refresh(user)
        return user.to_json()


def update_user(acting_user_id: UUID, user_id: UUID,
                role: Role | None, is_active: bool | None, password: str | None,
                unlock: bool | None = None) -> dict:
    # An admin can not lock themself out, hence there is always one active admin left.
    if user_id == acting_user_id and (
            (role is not None and role != Role.ADMIN) or is_active is False):
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "You can not demote or deactivate yourself.")

    with Session(get_engine()) as session:
        user = get_or_404(session, user_id)

        if user.auth_source == "ad":
            # His role comes from his groups at each login, and the directory owns his password.
            if role is not None:
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    "The role of a user of the Active Directory comes from his groups: change the role of "
                    "the group in the settings of the directory.")
            if password is not None:
                raise HTTPException(status.HTTP_409_CONFLICT,
                                    "The password of a user of the Active Directory is changed in the directory.")

        if role is not None:
            user.role = role.value
        if is_active is not None:
            user.is_active = is_active
        if password is not None:
            user.password_hash = hash_password(password)
        # A new password, like an explicit unlock, ends the lock.
        if unlock or password is not None:
            user.failed_attempts = 0
            user.locked_until = None

        session.add(user)
        session.commit()
        session.refresh(user)
        return user.to_json()


def delete_user(acting_user_id: UUID, user_id: UUID):
    if user_id == acting_user_id:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "You can not delete yourself.")

    with Session(get_engine()) as session:
        session.delete(get_or_404(session, user_id))
        session.commit()
