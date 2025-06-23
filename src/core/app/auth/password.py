from pydantic import Json
import sqlalchemy
from sqlmodel import Session, select
import bcrypt
import jwt
from app.database import init_db_connection, User
from app.environment import get_env_var


def __bytes_from_string(text: str) -> bytes:
    return bytes(text, "utf-8")


def __hash_password(password: str) -> bytes:
    return bcrypt.hashpw(__bytes_from_string(password), bcrypt.gensalt())


def __check_password(password: str, hash: bytes) -> bool:
    return bcrypt.checkpw(__bytes_from_string(password), hash)


def __get_private_key():
    return "TODO private key"


def register(username: str, password: str):
    hash: bytes = __hash_password(password)

    # Enough space must be reserved in the table column.
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

        if not __check_password(password, user.password_hash):
            raise Exception("Wrong password")

        return jwt.encode({
            "username": username,
        }, __get_private_key(), algorithm="HS256")


def change(username: str, old_password, new_password):
    engine = init_db_connection()
    with Session(engine) as session:
        statement = select(User).where(User.name == username)
        results = session.exec(statement)
        user: User = results.one()

        if not __check_password(old_password, user.password_hash):
            raise Exception("Wrong password")

        user.password_hash = __hash_password(new_password)
        session.add(user)
        session.commit()


def verify(token: str) -> Json:
    decoded = jwt.decode(token,
                         __get_private_key(),
                         algorithms=["HS256"])
    if decoded["username"] != get_env_var("DEFAULT_USER_NAME"):
        raise Exception("You must use the default user.")
    return decoded


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

from pydantic import Json
import sqlalchemy
from sqlmodel import Session, select
import bcrypt
import jwt
from app.database import init_db_connection, User
from app.environment import get_env_var


def __bytes_from_string(text):
    return bytes(text, "utf-8")


def __hash_password(password):
    return bcrypt.hashpw(__bytes_from_string(password), bcrypt.gensalt())


def __check_password(password, hash):
    return bcrypt.checkpw(__bytes_from_string(password), __bytes_from_string(hash))


def __get_private_key():
    return "TODO private key"


def register(username: str, password: str):
    hash = __hash_password(password)

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

        if not __check_password(password, user.password_hash):
            raise Exception("Wrong password")

        return jwt.encode({
            "username": username,
        }, __get_private_key(), algorithm="HS256")


def change(username: str, old_password, new_password):
    engine = init_db_connection()
    with Session(engine) as session:
        statement = select(User).where(User.name == username)
        results = session.exec(statement)
        user: User = results.one()

        if not __check_password(old_password, user.password_hash):
            raise Exception("Wrong password")

        user.password_hash = __hash_password(new_password)
        session.add(user)
        session.commit()


def verify(token: str) -> Json:
    decoded = jwt.decode(token,
                         __get_private_key(),
                         algorithms=["HS256"])
    if decoded["username"] != get_env_var("DEFAULT_USER_NAME"):
        raise Exception("You must use the default user.")
    return decoded


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
