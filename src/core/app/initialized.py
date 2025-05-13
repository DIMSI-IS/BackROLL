from fastapi import FastAPI, Form, Request
from pydantic_settings import BaseSettings
from starlette.middleware.cors import CORSMiddleware

import celery
from celery import Celery, states
from celery.backends.redis import RedisBackend
from celery.schedules import crontab

from kombu import Queue


class Settings(BaseSettings):
    app_name: str = 'BackupAPI'
    broker_url: str = 'redis://redis:6379/0'
    beat_scheduler: str = 'redbeat.RedBeatScheduler'
    beat_max_loop_interval: int = 5
    worker_max_tasks_per_child: int = 200
    worker_max_memory_per_child: int = 16384
    broker_transport_options: object = {'visibility_timeout': 43200}
    result_backend: str = 'redis://redis:6379/0'
    enable_utc: bool = False
    result_extended: bool = True
    timezone: str = 'Europe/Paris'
    task_default_queue: str = 'default'
    task_queues: tuple = (
        Queue('default',    routing_key='task.#'),
        Queue('backup_tasks', routing_key='backup.#'),
        Queue('setup_tasks', routing_key='setup.#')
    )
    task_default_exchange: str = 'tasks'
    task_default_exchange_type: str = 'topic'
    task_default_routing_key: str = 'task.default'


settings = Settings()
app = FastAPI()

origins = [
    "*"
]

# Using an outer CORS middleware (from starlette)
# to properly add CORS header
# to auto-generated status-code-500 responses.
starlette_app = CORSMiddleware(app=app,
                               allow_origins=origins,
                               allow_credentials=True,
                               allow_methods=["*"],
                               allow_headers=["Authorization"],
                               )


def patch_celery():
    """Patch redis backend."""

    def _unpack_chord_result(
        self, tup, decode,
        EXCEPTION_STATES=states.EXCEPTION_STATES,
        PROPAGATE_STATES=states.PROPAGATE_STATES,
    ):
        _, tid, state, retval = decode(tup)

        if state in EXCEPTION_STATES:
            retval = self.exception_to_python(retval)
        if state in PROPAGATE_STATES:
            # retval is an Exception
            return '{}: {}'.format(retval.__class__.__name__, str(retval))

        return retval

    celery.backends.redis.RedisBackend._unpack_chord_result = _unpack_chord_result

    return celery


# Initialize Celery
celery = patch_celery().Celery('BackupAPI', broker='redis://redis:6379/0')

celery.conf.ONCE = {
    'backend': 'celery_once.backends.Redis',
    'settings': {
        'url': 'redis://redis:6379/0',
        'default_timeout': 60 * 60 * 12
    }
}
celery.conf.update(settings)

celery.conf.update(
    result_expires=604800
)

# celery.conf.beat_schedule = {
#    'daily_routine_cleaning_backups': {
#        'task': 'garbageCollector',
#        'schedule': crontab(hour=1, minute=0, day_of_week='*', day_of_month='*', month_of_year='*'),
#        'args': ()
#    }
# }
