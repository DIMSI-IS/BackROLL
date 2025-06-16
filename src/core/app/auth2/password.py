import sqlalchemy
from sqlmodel import Session, select
import bcrypt
import jwt
from app.database import init_db_connection, User
from app.environment import get_env_var


def __get_private_key():
    return "TODO private key"


def register(username: str, password: str):
    hash = bcrypt.hashpw(bytes(password, "utf-8"), bcrypt.gensalt())

    user = User(name=username, password_hash=hash)
    engine = init_db_connection()
    with Session(engine) as session:
        session.add(user)
        session.commit()


def login(username: str, password: str) -> str:
    engine = init_db_connection()
    with Session(engine) as session:
        statement = select(User).where(User.name == username)
        results = session.exec(statement)
        user: User = results.one()

        if bcrypt.checkpw(bytes(password, "utf-8"), bytes(user.password_hash, "utf-8")):
            return jwt.encode({
                "username": username,
            }, __get_private_key(), algorithm="HS256")


def change(username: str, old_password, new_password):
    engine = init_db_connection()
    with Session(engine) as session:
        statement = select(User).where(User.name == username)
        results = session.exec(statement)
        user: User = results.one()

        if not bcrypt.checkpw(old_password, user.password_hash):
            raise Exception()

        user.password_hash = bcrypt.hashpw(new_password)
        session.add(user)
        session.commit()


def verify(token: str) -> bool:
    print(f"Inspect token at https://jwt.io/#id_token={token}.")
    decoded = jwt.decode(token,
                         __get_private_key(),
                         algorithms=["HS256"])
    print(f"{decoded=}")
    return decoded["username"] == get_env_var("DEFAULT_USER_NAME")


def ensure_default_user():
    engine = init_db_connection()
    with Session(engine) as session:
        statement = select(User).where(
            User.name == get_env_var("DEFAULT_USER_NAME"))
        results = session.exec(statement)
        try:
            results.one()
        except sqlalchemy.exc.NoResultFound:
            register(get_env_var("DEFAULT_USER_NAME"),
                     get_env_var("DEFAULT_USER_PASSWORD"))
