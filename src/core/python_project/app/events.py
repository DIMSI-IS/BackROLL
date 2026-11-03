from sqlmodel import SQLModel
from celery.signals import celeryd_init

from app.initialized import fastapi_app
from app.database import init_db_connection, migrate_policy_table, migrate_task_run_table, migrate_user_table, migrate_audit_table, migrate_secrets
from app.auth import token
from app import audit, cleanup, drp_history, file_browser, retention, ssh, storage_alert, task_history
from app.routes import cleanup as cleanup_routes
from app.routes.file_browser import get_storage_paths


@fastapi_app.on_event("startup")
async def on_api_startup():
    token.check_configuration()

    engine = init_db_connection()

    # If DB is not yet configured, proceed to initialization
    SQLModel.metadata.create_all(engine)
    migrate_user_table(engine)
    migrate_policy_table(engine)
    migrate_task_run_table(engine)
    migrate_audit_table(engine)
    migrate_secrets(engine)
    retention.start_cleaner()
    storage_alert.start_checker()
    cleanup.mark_interrupted()
    cleanup_routes.sync_all_schedules()
    drp_history.mark_interrupted()
    file_browser.start_cleaner(get_storage_paths)

    ssh.push_ssh_directory()
    ssh.ensure_configuration()


@celeryd_init.connect
def on_worker_startup(**kwargs):
    # Keyword arguments are required :
    # ValueError: Signal receiver must accept keyword arguments.

    ssh.ensure_configuration()
