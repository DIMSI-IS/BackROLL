from sqlmodel import SQLModel
from celery.signals import celeryd_init

from app.initialized import fastapi_app
from app.database import init_db_connection
from app.auth.password import ensure_default_user
from app import ssh


@fastapi_app.on_event("startup")
async def on_api_startup():
    engine = init_db_connection()

    # If DB is not yet configured, proceed to initialization
    SQLModel.metadata.create_all(engine)

    ensure_default_user()

    ssh.push_ssh_directory()
    ssh.ensure_configuration()


@celeryd_init.connect
def on_worker_startup(**kwargs):
    # Keyword arguments are required :
    # ValueError: Signal receiver must accept keyword arguments.

    ssh.ensure_configuration()
