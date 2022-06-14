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
import shutil
import uuid as uuid_pkg
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field, Json
from sqlmodel import Session, select
from fastapi.encoders import jsonable_encoder
from celery import Celery, states
from celery.exceptions import Ignore

from app import app
from app import celery as celeryWorker
from app import celery

from app import auth
from app import database
from app.database import Storage

@app.get('/api/v1/storage', status_code=202)
def list_storage(identity: Json = Depends(auth.valid_token)):
  task = retrieve_storage.delay()
  return {'Location': app.url_path_for('retrieve_task_status', task_id=task.id)}

@celery.task(name='List registered storage')
def retrieve_storage():
  try:
    engine = database.init_db_connection()
  except Exception as e:
    raise HTTPException(status_code=500, detail=jsonable_encoder(e))
  records = []
  with Session(engine) as session:
      statement = select(Storage)
      results = session.exec(statement)
      for storage in results:
        records.append(storage)
  
  result = jsonable_encoder(records)

  for item in result:
    usage_info = shutil.disk_usage(item['path'])
    d=usage_info._asdict()
    dct=dict(d)
    item['info'] = dct
    print(item)

  return jsonable_encoder(result)