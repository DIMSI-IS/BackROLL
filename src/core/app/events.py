from sqlmodel import SQLModel
from celery.signals import celeryd_init

from app import ssh
from app.initialized import fastapi_app
from app.database import init_db_connection
from app.auth.password import ensure_default_user


@fastapi_app.on_event("startup")
async def on_api_startup():
    engine = init_db_connection()

    # If DB is not yet configured, proceed to initialization
    SQLModel.metadata.create_all(engine)

    ensure_default_user()
    # ssh.ensure_set_keys()
    ssh.get_keys()


@celeryd_init.connect
def on_worker_startup(**kwargs):
    # Keyword arguments are required :
    # ValueError: Signal receiver must accept keyword arguments.

    ssh.get_keys()
