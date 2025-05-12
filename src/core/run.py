# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
##
# http://www.apache.org/licenses/LICENSE-2.0
##
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

#! /usr/bin/env python
import uvicorn
import eventlet

# Importing the modules which define FastAPI routes and Celery tasks.

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

# eventlet.monkey_patch()

if __name__ == '__main__':
    uvicorn.run('app:outer_app', host='0.0.0.0', port=5050)
