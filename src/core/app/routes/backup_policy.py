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
import uuid as uuid_pkg
from croniter import croniter
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends
from fastapi.encoders import jsonable_encoder
from sqlmodel import Session, select
from pydantic import BaseModel, Json
from celery import Celery, states, chord
from celery.result import AsyncResult
from celery.schedules import crontab
from redbeat import RedBeatSchedulerEntry

from app import app
from app import auth
from app import database
from app.database import Policies
from app.database import Storage
from app.database import Pools
from app.database import Hosts

from app.routes import external_hooks

from app import celery as celeryWorker
from app import celery

class backup_policy_create(BaseModel):
  name: str
  description: Optional[str] = None
  schedule: str
  retention: dict
  storage: uuid_pkg.UUID
  externalhook: Optional[str] = None
  enabled: Optional[bool] = False
  class Config:
      schema_extra = {
          "example": {
              "name": "example_policy",
              "description": "Daily backup routine (at midnight)",
              "schedule": "0 0 * * *",
              "retention_day": "1",
              "retention_week": "1",
              "retention_month": "1",
              "retention_year": "1",
              "storage": "7984bbc7-d202-4603-834f-5d1a5bf0e33e",
              "externalhook": "https://my.example-webhook.com/ud4jf"
          }
      }

class backup_policy_update(BaseModel):
  name: Optional[str] = None
  description: Optional[str] = None
  schedule: Optional[str] = None
  retention: Optional[dict] = None
  storage: Optional[uuid_pkg.UUID] = None
  externalhook: Optional[str] = None
  enabled: Optional[bool] = None
  class Config:
      schema_extra = {
          "example": {
              "name": "example_policy",
              "description": "Daily backup routine (at midnight)",
              "schedule": "0 0 * * *",
              "retention_day": "1",
              "retention_week": "1",
              "retention_month": "1",
              "retention_year": "1",
              "storage": "7984bbc7-d202-4603-834f-5d1a5bf0e33e",
              "externalhook": "https://my.example-webhook.com/ud4jf"
          }
      }

def filter_policy_by_id(policy_id):
  try:
    engine = database.init_db_connection()
  except Exception as e:
    raise ValueError(e)
  try:
    with Session(engine) as session:
      statement = select(Policies).where(Policies.id == policy_id)
      results = session.exec(statement)
      policy = results.one()
      if not policy:
        raise ValueError(f'Policy with id {policy_id} not found')
    return policy
  except Exception as e:
    raise ValueError(e)

@celery.task(name='create_backup_policy')
def api_create_backup_policy(name, description, schedule, retention, storage, externalhook):
  try:
    engine = database.init_db_connection()
  except Exception as e:
    raise ValueError(e)
  try:
    new_policy = Policies(name=name, description=description, schedule=schedule, retention_day=retention["day"], retention_week=retention["week"], retention_month=retention["month"], retention_year=retention["year"], storage=storage, externalhook=externalhook)
    with Session(engine) as session:
        session.add(new_policy)
        session.commit()
        session.refresh(new_policy)
        return new_policy
  except Exception as e:
    raise ValueError(e)

@celery.task(name='delete_backup_policy')
def api_delete_backup_policy(backup_policy_id):
  try:
    engine = database.init_db_connection()
  except Exception as e:
    raise ValueError(e)
  try:
    with Session(engine) as session:
      statement = select(Policies).where(Policies.id == backup_policy_id)
      results = session.exec(statement)
      policy = results.one()
      if not policy:
        raise ValueError(f'Backup policy with id {backup_policy_id} not found')
      session.delete(policy)
      session.commit()
      return {'state': 'SUCCESS'}
  except Exception as e:
    raise ValueError(e)

@celery.task(name='List backup policies')
def retrieve_backup_policies():
  try:
    engine = database.init_db_connection()
  except Exception as e:
    raise ValueError(e)
  try:
    records = []
    with Session(engine) as session:
        statement = select(Policies)
        results = session.exec(statement)
        for policy in results:
          records.append(policy)
    return jsonable_encoder(records)
  except Exception as e:
    raise ValueError(e)

def api_update_backup_policy(policy_id, name, description, schedule, retention, storage, externalhook, enabled):
  try:
    engine = database.init_db_connection()
  except:
    raise ValueError('Unable to connect to database.')
  with Session(engine) as session:
    statement = select(Policies).where(Policies.id == policy_id)
    results = session.exec(statement)
    data_backup_policy = results.one()

  if not data_backup_policy:
    raise ValueError(f'backup policy with id {policy_id} not found')
  task = "Kickstart_Pool_Backup"
  if schedule:
    split_cron = schedule.split()
  else:
    split_cron = data_backup_policy.schedule.split()
  if name: policy_name = name
  else: policy_name = data_backup_policy.name

  try:
    data_pool = []
    with Session(engine) as session:
      statement = select(Pools).where(Pools.policy_id == policy_id)
      results = session.exec(statement)
      for pool in results:
        data_pool.append(pool)
  except Exception as e:
    raise ValueError(e)

  if data_backup_policy.enabled == 1:
    if not data_pool: raise ValueError(f'backup policy with id {policy_id} has no pool associated to it')
    for pool in data_pool:
      currentPool = pool.to_json()
      try:
        unique_task_name = f"{task}-{data_backup_policy.name}-{data_backup_policy.id}-{currentPool['name']}"
        key = f"redbeat:{unique_task_name}"
        e = RedBeatSchedulerEntry.from_key(key, app=celery)
        try:
          e.delete()
        except Exception as e:
          raise ValueError(e)
      except:
        raise ValueError(f'Unable to disable backup policy with id {policy_id} as the scheduled task was not found.')
  if enabled == True:
    if not data_pool: raise ValueError(f'backup policy with id {policy_id} has no pool associated to it')
    for pool in data_pool:
      try:
        data_host = []
        with Session(engine) as session:
          statement = select(Hosts).where(Hosts.pool_id == pool.id)
          results = session.exec(statement)
          for host in results:
            data_host.append(host)
        if not data_host: raise ValueError(f'backup policy with id {policy_id} has one or more empty pool associated to it')
      except Exception as e:
        raise ValueError(e)
      try:
        currentPool = pool.to_json()
        unique_task_name = f"{task}-{policy_name}-{policy_id}-{currentPool['name']}"
        entry = RedBeatSchedulerEntry(unique_task_name, task, crontab(minute=split_cron[0], hour=split_cron[1], day_of_month=split_cron[2], month_of_year=split_cron[3], day_of_week=split_cron[4]), args=(currentPool['id'],), app=celery)
        entry.save()
      except Exception as e:
        raise ValueError(e)
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
      data_backup_policy.retention_day = retention["day"]
      data_backup_policy.retention_week = retention["week"]
      data_backup_policy.retention_month = retention["month"]
      data_backup_policy.retention_year = retention["year"]
    if storage:
      data_backup_policy.storage = storage
    if externalhook is not None:
      external_hooks.filter_external_hook_by_id(externalhook)
      data_backup_policy.externalhook = externalhook
    else:
      data_backup_policy.externalhook = None
    with Session(engine) as session:
      session.add(data_backup_policy)
      session.commit()
      session.refresh(data_backup_policy)
    return jsonable_encoder(data_backup_policy)
  except Exception as e:
    raise ValueError(e)

@app.post("/api/v1/backup_policies", status_code=201)
def create_backup_policy(item: backup_policy_create, identity: Json = Depends(auth.valid_token)):
  try:
    engine = database.init_db_connection()
  except Exception as e:
    raise HTTPException(status_code=500, detail=jsonable_encoder(e))
  records = []
  with Session(engine) as session:
    statement = select(Storage).where(Storage.id == item.storage)
    results = session.exec(statement)
    for policy in results:
      records.append(policy)
    if len(records) < 1:
      reason = f'Specified storage hasn\'t been found'
      raise HTTPException(status_code=500, detail=reason)
  name = item.name
  description = item.description
  schedule = item.schedule
  retention = item.retention
  storage = item.storage
  externalhook = item.externalhook
  return api_create_backup_policy(name, description, schedule, retention, storage, externalhook)

@app.get("/api/v1/backup_policies", status_code=202)
def list_backup_policies(identity: Json = Depends(auth.valid_token)):
    task = retrieve_backup_policies.delay()
    return {'Location': app.url_path_for('retrieve_task_status', task_id=task.id)}

@app.patch("/api/v1/backup_policies/{policy_id}", status_code=200)
def update_backup_policy(policy_id, item: backup_policy_update, identity: Json = Depends(auth.valid_token)):
  name = item.name
  description = item.description
  schedule = item.schedule
  retention = item.retention
  storage = item.storage
  externalhook = item.externalhook
  enabled = item.enabled

  if schedule and not croniter.is_valid(schedule):
    raise HTTPException(status_code=400, detail='Provided crontab format is invalid')
  if enabled:
    if not type(enabled)==bool:
      raise HTTPException(status_code=400, detail='Provided enabled status is invalid (must be true/false)')
  return api_update_backup_policy(policy_id, name, description, schedule, retention, storage, externalhook, enabled)

@app.delete("/api/v1/backup_policies/{policy_id}", status_code=200)
def delete_backup_policy(policy_id: str, identity: Json = Depends(auth.valid_token)):
  try:
    engine = database.init_db_connection()
  except Exception as e:
    raise HTTPException(status_code=500, detail=jsonable_encoder(e))
  records = []
  with Session(engine) as session:
    statement = select(Pools).where(Pools.policy_id == policy_id)
    results = session.exec(statement)
    for policy in results:
      records.append(policy)
    if len(records) > 0:
      reason = f'One or more pools are linked to this policy'
      raise HTTPException(status_code=500, detail=reason)
  return api_delete_backup_policy(policy_id)