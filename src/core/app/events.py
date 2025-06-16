from sqlmodel import SQLModel
from app.initialized import fastapi_app
from app.database import init_db_connection
from app.auth.password import ensure_default_user


@fastapi_app.on_event("startup")
async def startup_event():
    engine = init_db_connection()

    # If DB is not yet configured, proceed to initialization
    SQLModel.metadata.create_all(engine)

    ensure_default_user()
