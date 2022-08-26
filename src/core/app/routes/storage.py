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

from app import celery

from app import auth
from app import database
from app.database import Hosts
from app.database import Pools
from app.database import Policies
from app.database import Storage

class items_storage(BaseModel):
  name: str
  path: str
  class Config:
      schema_extra = {
          "example": {
              "name": "example_storage",
              "path": "/path/to/my/storage_backend"
          }
      }

def retrieveStoragePathFromHostBackupPolicy(virtual_machine_info):
  try:
    engine = database.init_db_connection()
  except Exception as e:
    raise HTTPException(status_code=500, detail=jsonable_encoder(e))
  try:
    with Session(engine) as session:
      # Find host linked to vm
      statement = select(Hosts).where(Hosts.id == virtual_machine_info['host'])
      results = session.exec(statement)
      host = results.one()
      if not host:
        reason = f"Host with id {virtual_machine_info['host']} not found"
        raise HTTPException(status_code=404, detail=reason)
      # Find pool linked to host
      statement = select(Pools).where(Pools.id == host.pool_id)
      results = session.exec(statement)
      pool = results.one()
      if not pool:
        reason = f"Pool with id {host_info['pool_id']} not found"
        raise HTTPException(status_code=404, detail=reason)
      # Find policy linked to pool
      statement = select(Policies).where(Policies.id == pool.policy_id)
      results = session.exec(statement)
      policy = results.one()
      if not policy:
        reason = f"Policy with id {pool.policy_id} not found"
        raise HTTPException(status_code=404, detail=reason)
      # Find policy linked to pool
      statement = select(Storage).where(Storage.id == policy.storage)
      results = session.exec(statement)
      storage = results.one()
      if not storage:
        reason = f"Storage with id {policy.storage} not found"
        raise HTTPException(status_code=404, detail=reason)
    return storage.to_json()
  except Exception as e:
    raise HTTPException(status_code=500, detail=jsonable_encoder(e))

def filter_storage_by_id(storage_id):
  try:
    engine = database.init_db_connection()
  except Exception as e:
    raise HTTPException(status_code=500, detail=jsonable_encoder(e))
  try:
    with Session(engine) as session:
      statement = select(Storage).where(Storage.id == storage_id)
      results = session.exec(statement)
      storage = results.one()
      if not storage:
        reason = f'Storage with id {storage_id} not found'
        raise HTTPException(status_code=404, detail=reason)
    return storage
  except Exception as e:
    raise HTTPException(status_code=500, detail=jsonable_encoder(e))

@celery.task(name='create storage')
def api_create_storage(name, path):
  try:
    engine = database.init_db_connection()
  except Exception as e:
    raise HTTPException(status_code=500, detail=jsonable_encoder(e))
  try:
    new_storage = Storage(name=name, path=path)
    with Session(engine) as session:
        session.add(new_storage)
        session.commit()
        session.refresh(new_storage)
    return new_storage
  except Exception as e:
    raise HTTPException(status_code=400, detail=jsonable_encoder(e))

@celery.task(name='Update storage')
def api_update_storage(storage_id, name, path):
  try:
    engine = database.init_db_connection()
  except:
    raise HTTPException(status_code=500, detail='Unable to connect to database.')
  with Session(engine) as session:
    statement = select(Storage).where(Storage.id == storage_id)
    results = session.exec(statement)
    data_storage = results.one()
  if not data_storage:
    raise HTTPException(status_code=404, detail=f'Storage with id {storage_id} not found')
  try:
    if name:
      data_storage.name = name
    if path:
      data_storage.path = path
    with Session(engine) as session:
      session.add(data_storage)
      session.commit()
      session.refresh(data_storage)
    return jsonable_encoder(data_storage)
  except Exception as e:
    print(e)
    raise HTTPException(status_code=500, detail=jsonable_encoder(e))

@celery.task(name='Delete storage')
def api_delete_storage(storage_id):
  try:
    engine = database.init_db_connection()
  except Exception as e:
    raise HTTPException(status_code=500, detail=jsonable_encoder(e))
  records = []
  with Session(engine) as session:
    statement = select(Policies).where(Policies.storage == storage_id)
    results = session.exec(statement)
    for policy in results:
      records.append(policy)
    print(records)
    if len(records) > 0:
      reason = f'One or more policies are linked to this storage'
      raise HTTPException(status_code=500, detail=reason)
  try:
    storage = filter_storage_by_id(storage_id)
    with Session(engine) as session:
      session.delete(storage)
      session.commit()
    return {'state': 'SUCCESS'}
  except Exception as e:
    raise HTTPException(status_code=400, detail=jsonable_encoder(e))  

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
    try:
      usage_info = shutil.disk_usage(item['path'])
      d=usage_info._asdict()
      dct=dict(d)
      item['info'] = dct
    except:
      item['info'] = None
  return jsonable_encoder(result)

@app.get('/api/v1/storage', status_code=202)
def list_storage(identity: Json = Depends(auth.valid_token)):
  task = retrieve_storage.delay()
  return {'Location': app.url_path_for('retrieve_task_status', task_id=task.id)}

@app.post('/api/v1/storage', status_code=201)
def create_storage(item: items_storage, identity: Json = Depends(auth.valid_token)):
  name = item.name
  path = item.path
  return api_create_storage(name, path)

@app.patch("/api/v1/storage/{storage_id}", status_code=200)
def update_storage(storage_id, item: items_storage, identity: Json = Depends(auth.valid_token)):
  try:
      uuid_obj = uuid_pkg.UUID(storage_id)
  except ValueError:
      raise HTTPException(status_code=404, detail='Given uuid is not valid')
  name = item.name
  path = item.path
  return api_update_storage(storage_id, name, path)

@app.delete('/api/v1/storage/{storage_id}', status_code=200)
def delete_storage(storage_id: str, identity: Json = Depends(auth.valid_token)):
  try:
    uuid_obj = uuid_pkg.UUID(storage_id)
  except ValueError:
    raise HTTPException(status_code=404, detail='Given uuid is not valid')
  if not storage_id: raise HTTPException(status_code=404, detail='Pool not found')
  return api_delete_storage(storage_id)