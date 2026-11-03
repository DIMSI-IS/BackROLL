# Importing files with decorated functions to register FastAPI routes and Celery tasks.
# TODO Separate routes and tasks ?

from app.scheduler import retrieve_tasks

from app import task_handler

from app.borg import borg_misc

from app.backup_tasks import single_backup
from app.backup_tasks import pool_backup
from app import restore

from app import auth
from app.routes import job
from app.routes import task
from app.routes import virtual_machine
from app.routes import pool
from app.routes import host
from app.routes import external_hooks
from app.routes import backup_policy
from app.routes import storage
from app.routes import kickstart_backup
from app.routes import connectors
from app.routes import users
from app.routes import audit
from app.routes import settings
from app.routes import dashboard
from app.routes import cleanup as cleanup_routes
from app.routes import file_browser
from app.routes import attention
from app import drp
from app.routes import drp as drp_routes
from app.routes.auth import password, cloudstack
from app.routes.auth import directory as directory_routes

from app import events
from app import task_history

# Re-export
from app.initialized import starlette_app, celery_app
starlette_app = starlette_app
celery_app = celery_app
