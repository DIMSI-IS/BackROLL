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
import json
from croniter import croniter
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends
from fastapi.encoders import jsonable_encoder
from sqlmodel import Session, select
from pydantic import BaseModel, Json
from celery import Celery, states
from celery.result import AsyncResult
from celery.schedules import crontab
from redbeat import RedBeatSchedulerEntry

from app import app
from app import auth
from app import database
from app.database import Policies
from app.database import Pools
from app.database import Hosts
from app import celery as celeryWorker
from app import celery

class backup_policy_create(BaseModel):
  name: str
  description: str
  class Config:
      schema_extra = {
          "example": {
              "name": "example_policy",
              "description": "This is my description"
          }
      }

class backup_policy_update(BaseModel):
  name: Optional[str] = None
  description: Optional[str] = None
  schedule: Optional[str] = None
  retention: Optional[dict] = None
  enabled: Optional[bool] = None
  class Config:
      schema_extra = {
          "example": {
              "name": "example_policy",
              "description": "Daily backup routine (at midnight)",
              "schedule": "0 0 * * *",
              "retention": {"daily":7, "weekly":1, "monthly":1, "yearly":0},
              "enabled": True
          }
      }

@celery.task(name='create_backup_policy')
def api_create_backup_policy(name, description):
  try:
    engine = database.init_db_connection()
  except Exception as e:
    raise HTTPException(status_code=500, detail=jsonable_encoder(e))
  try:
    new_policy = Policies(name=name, description=description, schedule='0 0 1 * *', retention='{"daily":0, "weekly":0, "monthly":0, "yearly":0}')
    with Session(engine) as session:
        session.add(new_policy)
        session.commit()
        session.refresh(new_policy)
        return new_policy
  except Exception as e:
    print(e)
    raise HTTPException(status_code=500, detail=jsonable_encoder(e))

@celery.task(name='delete_backup_policy')
def api_delete_backup_policy(backup_policy_id):
  try:
    engine = database.init_db_connection()
  except Exception as e:
    raise HTTPException(status_code=500, detail=jsonable_encoder(e))
  try:
    with Session(engine) as session:
      statement = select(Policies).where(Policies.id == backup_policy_id)
      results = session.exec(statement)
      policy = results.one()
      if not policy:
        reason = f'Backup policy with id {backup_policy_id} not found'
        raise HTTPException(status_code=404, detail=reason)
      session.delete(policy)
      session.commit()
      return {'state': 'SUCCESS'}
  except Exception as e:
    raise HTTPException(status_code=500, detail=jsonable_encoder(e))

@celery.task(name='List backup policies')
def retrieve_backup_policies():
  try:
    engine = database.init_db_connection()
  except Exception as e:
    raise HTTPException(status_code=500, detail=jsonable_encoder(e))
  try:
    records = []
    with Session(engine) as session:
        statement = select(Policies)
        results = session.exec(statement)
        for policy in results:
          records.append(policy)
    return jsonable_encoder(records)
  except Exception as e:
    raise HTTPException(status_code=500, detail=jsonable_encoder(e))

def api_update_backup_policy(policy_id, name, description, schedule, retention, enabled):
  try:
    engine = database.init_db_connection()
  except:
    raise HTTPException(status_code=500, detail='Unable to connect to database.')
  with Session(engine) as session:
    statement = select(Policies).where(Policies.id == policy_id)
    results = session.exec(statement)
    data_backup_policy = results.one()

  if not data_backup_policy:
    raise HTTPException(status_code=404, detail=f'backup policy with id {policy_id} not found')
  task = "Pool_VM_Backup"
  if schedule:
    split_cron = schedule.split()
  else:
    split_cron = data_backup_policy.schedule.split()
  if name: policy_name = name
  else: policy_name = data_backup_policy.name

  if data_backup_policy.enabled == 1:
    try:
      unique_task_name = f"{task}-{data_backup_policy.name}-{data_backup_policy.id}"
      key = f"redbeat:{unique_task_name}"
      e = RedBeatSchedulerEntry.from_key(key, app=celery)
      try:
        e.delete()
      except Exception as e:
        raise HTTPException(status_code=500, detail=jsonable_encoder(e))
    except:
      raise HTTPException(status_code=500, detail=f'Unable to disable backup policy with id {policy_id} as the scheduled task was not found.')
  if enabled == True:
    try:
      data_pool = []
      with Session(engine) as session:
        statement = select(Pools).where(Pools.policy_id == policy_id)
        results = session.exec(statement)
        for pool in results:
          data_pool.append(pool)
      if not data_pool: raise HTTPException(status_code=500, detail=f'backup policy with id {policy_id} has no pool associated to it')
    except Exception as e:
      raise HTTPException(status_code=500, detail=jsonable_encoder(e))
    try:
      data_host = []
      with Session(engine) as session:
        statement = select(Hosts).where(Hosts.pool_id == pool.id)
        results = session.exec(statement)
        for host in results:
          data_host.append(host)
      if not data_host: raise HTTPException(status_code=500, detail=f'backup policy with id {policy_id} only has empty pool associated to it')
    except Exception as e:
      raise HTTPException(status_code=500, detail=jsonable_encoder(e))
    try:

      unique_task_name = f"{task}-{policy_name}-{policy_id}"
      entry = RedBeatSchedulerEntry(unique_task_name, task, crontab(minute=split_cron[0], hour=split_cron[1], day_of_month=split_cron[2], month_of_year=split_cron[3], day_of_week=split_cron[4]), args=(jsonable_encoder(data_host),), app=celery)
      entry.save()
    except:
      raise HTTPException(status_code=500, detail='Unable to enable this backup policy.')
  try:
    if enabled == True:
      data_backup_policy.enabled = 1
    else:
      data_backup_policy.enabled = 0
    if name:
      data_backup_policy.name = name
    if description:
      data_backup_policy.description = description
    if schedule:
      data_backup_policy.schedule = schedule
    if retention:
      data_backup_policy.retention = json.dumps(retention)
    with Session(engine) as session:
      session.add(data_backup_policy)
      session.commit()
      session.refresh(data_backup_policy)
    return jsonable_encoder(data_backup_policy)
  except Exception as e:
    print(e)
    raise HTTPException(status_code=500, detail=jsonable_encoder(e))

@app.post("/api/v1/backup_policies", status_code=201)
def create_backup_policy(item: backup_policy_create, identity: Json = Depends(auth.valid_token)):
  name = item.name
  description = item.description
  return api_create_backup_policy(name, description)

@app.get("/api/v1/backup_policies", status_code=202)
def list_backup_policies():
    task = retrieve_backup_policies.delay()
    return {'Location': app.url_path_for('retrieve_task_status', task_id=task.id)}

@app.patch("/api/v1/backup_policies/{policy_id}", status_code=200)
def update_backup_policy(policy_id, item: backup_policy_update, identity: Json = Depends(auth.valid_token)):
  name = item.name
  description = item.description
  schedule = item.schedule
  retention = item.retention
  enabled = item.enabled

  if schedule and not croniter.is_valid(schedule):
    raise HTTPException(status_code=400, detail='Provided crontab format is invalid')
  if enabled:
    if not type(enabled)==bool:
      raise HTTPException(status_code=400, detail='Provided enabled status is invalid (must be true/false)')
  return api_update_backup_policy(policy_id, name, description, schedule, retention, enabled)

@app.delete("/api/v1/backup_policies/{policy_id}", status_code=200)
def delete_backup_policy(policy_id: str, identity: Json = Depends(auth.valid_token)):
  return api_delete_backup_policy(policy_id)