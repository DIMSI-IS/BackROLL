from app import database

def register(username: str, password: str):
    user = User(id = )
    engine = database.init_db_connection()
    with Session(engine) as session:
        session.add(new_policy)
        session.commit()
        session.refresh(new_policy)
        return new_policy


def token(username: str, password: str) -> str:
    pass


def verify(token: str) -> bool:
    pass
