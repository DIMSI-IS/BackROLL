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
import os
import uuid as uuid_pkg
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field, Json
from fastapi.encoders import jsonable_encoder
from celery import Celery, states
from celery.exceptions import Ignore
import requests
from requests.auth import HTTPBasicAuth
import json

from sqlmodel import Session, select
from app.kvm import kvm_list_vm
from celery import chord

from app import app
from app import celery
from celery import chain
from celery import current_app

from app import task_handler
from app.backup_tasks import single_backup
from app.backup_tasks import pool_backup

from app.routes import host
from app.routes import pool
from app.routes import virtual_machine

from app import auth
from app import database
from app import restore

from app.database import Hosts

class restorebackup_start(BaseModel):
  virtual_machine_id: str
  backup_id: str
  class Config:
      schema_extra = {
          "example": {
              "virtual_machine_id": "3414b922-a39f-11ec-b909-0242ac120002",
              "backup_id": "3f0dffaa-a39f-11ec-b909-0242ac120002",
          }
      }

@celery.task(name='restore_task_jobs')
def retrieve_restore_task_jobs():
  single_vm_payload = {"taskname": "VM_Restore_Disk"}
  single_vm_response = requests.get('http://flower:5555/api/tasks', auth=HTTPBasicAuth(os.getenv('FLOWER_USER'), os.getenv('FLOWER_PASSWORD')), params=single_vm_payload)
  single_vm_task = json.loads(single_vm_response.content.decode('ascii'))
  return single_vm_task

@celery.task(name='backuptask_jobs')
def retrieve_backup_task_jobs():
  single_vm_payload = {"taskname": "	Single_VM_Backup"}
  single_vm_response = requests.get('http://flower:5555/api/tasks', auth=HTTPBasicAuth(os.getenv('FLOWER_USER'), os.getenv('FLOWER_PASSWORD')), params=single_vm_payload)
  pool_payload = {"taskname": "Pool_VM_Backup"}
  pool_response = requests.get('http://flower:5555/api/tasks', auth=HTTPBasicAuth(os.getenv('FLOWER_USER'), os.getenv('FLOWER_PASSWORD')), params=pool_payload)
  subtask_payload = {"taskname": "backup_subtask"}
  subtask_response = requests.get('http://flower:5555/api/tasks', auth=HTTPBasicAuth(os.getenv('FLOWER_USER'), os.getenv('FLOWER_PASSWORD')), params=subtask_payload)
  single_vm_task = json.loads(single_vm_response.content.decode('ascii'))
  pool_vm_task = json.loads(pool_response.content.decode('ascii'))
  subtask = json.loads(subtask_response.content.decode('ascii'))
  aggregated_jobs_list = single_vm_task.copy()
  aggregated_jobs_list.update(pool_vm_task)
  aggregated_jobs_list.update(subtask)
  return aggregated_jobs_list

def get_task_logs(task_id):
  response = requests.get(f'http://flower:5555/api/task/info/{task_id}', auth=HTTPBasicAuth(os.getenv('FLOWER_USER'), os.getenv('FLOWER_PASSWORD')))
  return response.content

@app.get('/api/v1/status/{task_id}', status_code=200)
def retrieve_task_status(task_id, identity: Json = Depends(auth.valid_token)):
  try:
      uuid_obj = uuid_pkg.UUID(task_id)
  except ValueError:
      raise HTTPException(status_code=404, detail='Given uuid is not valid')
  task = celery.AsyncResult(task_id)
  if task.state == 'PENDING':
      response = {
          'state': task.state,
          'current': 0,
          'total': 1,
          'status': 'Pending...'
      }
      if task.info:
        response['current'] = task.info.get('current')
        response['total'] = task.info.get('total')
        response['percentage'] = task.info.get('percentage')
        response['step'] = task.info.get('step')
  elif task.state == 'PROGRESS':
      response = {
          'status': 'In progress...'
      }
      if task.info:
        response['current'] = task.info.get('current')
        response['total'] = task.info.get('total')
        response['percentage'] = task.info.get('percentage')
        response['step'] = task.info.get('step')
  elif task.state != 'FAILURE':
      response = {
          'state': task.state,
          'info': task.info
      }
      if task.info and 'result' in task.info:
        response['result'] = task.info['result']
  else:
      response = {
          'state': task.state,
          'current': 1,
          'total': 1,
          'status': str(task.info)
      }
  return response

@app.get('/api/v1/logs/{task_id}', status_code=200)
def retrieve_task_logs(task_id, identity: Json = Depends(auth.valid_token)):
  try:
      uuid_obj = uuid_pkg.UUID(task_id)
  except ValueError:
      raise HTTPException(status_code=404, detail='Given uuid is not valid')
  return get_task_logs(task_id)

@app.post('/api/v1/tasks/singlebackup/{virtual_machine_id}', status_code=202)
def start_vm_single_backup(virtual_machine_id, identity: Json = Depends(auth.valid_token)):
  try:
      uuid_obj = uuid_pkg.UUID(virtual_machine_id)
  except ValueError:
      raise HTTPException(status_code=404, detail='Given uuid is not valid')
  if not virtual_machine_id: raise HTTPException(status_code=404, detail='Virtual machine not found')
  res = chain(host.retrieve_host.s(), virtual_machine.dmap.s(virtual_machine.parse_host.s()), virtual_machine.handle_results.s(), virtual_machine.filter_virtual_machine_list.s(virtual_machine_id), single_backup.single_vm_backup.s()).apply_async()
  return {'Location': app.url_path_for('retrieve_task_status', task_id=res.id)}

@app.post('/api/v1/tasks/restore/{virtual_machine_id}', status_code=202)
def start_vm_restore(virtual_machine_id, item: restorebackup_start, identity: Json = Depends(auth.valid_token)):
  try:
      uuid_obj = uuid_pkg.UUID(virtual_machine_id)
  except ValueError:
      raise HTTPException(status_code=404, detail='Given uuid is not valid')
  virtual_machine_id = item.virtual_machine_id
  backup_id = item.backup_id
  res = chain(host.retrieve_host.s(), virtual_machine.dmap.s(virtual_machine.parse_host.s()), virtual_machine.handle_results.s(), virtual_machine.filter_virtual_machine_list.s(virtual_machine_id), restore.restore_disk_vm.s(backup_id)).apply_async() 
  return {'Location': app.url_path_for('retrieve_task_status', task_id=res.id)}

@app.get('/api/v1/tasks/backup', status_code=200)
def list_backup_tasks(identity: Json = Depends(auth.valid_token)): 
  return {'info': retrieve_backup_task_jobs()}

@app.get('/api/v1/tasks/restore', status_code=200)
def list_restore_tasks(identity: Json = Depends(auth.valid_token)): 
  return {'info': retrieve_restore_task_jobs()}