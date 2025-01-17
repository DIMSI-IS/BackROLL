## Licensed to the Apache Software Foundation (ASF) under one
## or more contributor license agreements.  See the NOTICE file
## distributed with this work for additional information
## regarding copyright ownership.  The ASF licenses this file
## to you under the Apache License, Version 2.0 (the
## "License"); you may not use this file except in compliance
## with the License.  You may obtain a copy of the License at
##
##   http://www.apache.org/licenses/LICENSE-2.0
##
## Unless required by applicable law or agreed to in writing,
## software distributed under the License is distributed on an
## "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
## KIND, either express or implied.  See the License for the
## specific language governing permissions and limitations
## under the License.

#! /usr/bin/env python

from fastapi import FastAPI, Form, Request
from pydantic_settings import BaseSettings
from fastapi.middleware.cors import CORSMiddleware

import celery
from celery import Celery, states
from celery.backends.redis import RedisBackend

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

app.add_middleware(
    CORSMiddleware,
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
celery.conf.resultrepr_maxsize = 4096



celery.conf.update(settings)

celery.conf.update(
  result_expires=604800
)

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

from app import main