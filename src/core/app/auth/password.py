from sqlmodel import Session, select
from app.database import init_db_connection, User
import bcrypt
import jwt


def register(username: str, password: str):
    hash = bcrypt.hashpw(password)

    user = User(name=username, password_hash=hash)
    engine = init_db_connection()
    with Session(engine) as session:
        session.add(user)
        session.commit()


def token(username: str, password: str) -> str:
    engine = init_db_connection()
    with Session(engine) as session:
        statement = select(User).where(User.name == username)
        results = session.exec(statement)
        user: User = results.one()

        if bcrypt.checkpw(password, user.password_hash):
            return jwt.encode({
                username: username
            })


def verify(token: str) -> bool:
    decoded = jwt.decode(token)
    

