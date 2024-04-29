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

#!/usr/bin/env python
from fastapi import HTTPException, Depends
from pydantic import Json
from fastapi.encoders import jsonable_encoder

from app import app
from app import celery

from app import auth

@celery.task()
def retrieve_job():
  try:
    return [
      {
      'name': 'Backup (VM)',
      'mode': 'single',
      'type': 'backup'
      },
      {
      'name': 'Backup (Pool)',
      'mode': 'pool',
      'type': 'backup'
      },
      {
      'name': 'Disk Restore & Replace (VM)',
      'mode': 'single',
      'type': 'restore'
      },
      {
      'name': 'Disk Restore To Specified Path',
      'mode': 'mounted',
      'type': 'restore'
      },
    ]
  except Exception as e:
    raise ValueError(e)

@app.get('/api/v1/jobs', status_code=202)
def list_available_jobs(identity: Json = Depends(auth.valid_token)):
    task = retrieve_job.delay()
    return {'Location': app.url_path_for('retrieve_task_status', task_id=task.id)}