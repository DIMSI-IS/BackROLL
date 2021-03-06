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
import uuid as uuid_pkg
from fastapi import FastAPI, HTTPException, Depends
from fastapi.encoders import jsonable_encoder
from pydantic import Json

from celery.result import allow_join_result
from celery import Celery, states
from celery.exceptions import Ignore
from celery import subtask, group, chain, chord, result

import json

from app import app
from app import celery as celeryWorker
from app import celery as celery_app

from app import auth
from app import database
from app.database import Hosts

from app.borg import borg_core
from app.borg import borg_misc

from app.routes import host

# KVM Imports
from app.kvm import kvm_check
from app.kvm import kvm_list_vm
from app.kvm import kvm_list_disk

@celery_app.task(name='filter_virtual_machine_list')
def filter_virtual_machine_list(virtual_machine_list, virtual_machine_id):
  for vm in virtual_machine_list:
    if vm['uuid'] == virtual_machine_id:
      break
  return vm

@celery_app.task(name='Parse Host instance(s)')
def parse_host(host):
  if host['state'] == 'Reachable' and host['ssh'] == 1:
    return kvm_list_vm.retrieve_virtualmachine(host)
  else:
    return []

@celery_app.task
def dmap(it, callback):
    # Map a callback over an iterator and return as a group
    callback = subtask(callback)
    c = group(callback.clone([arg,]) for arg in it)()
    c.save()
    return c.id

@celery_app.task
def handle_results(group_id):
  print(group_id)
  with allow_join_result():
    restored_group_result = celery_app.GroupResult.restore(group_id)
    result = restored_group_result.get()
  global_instance_list = []
  for instance_list in result:
    global_instance_list += instance_list
  return global_instance_list

@celery_app.task(name='List VMs backups', bind=True, max_retries=3)
def retrieve_virtual_machine_backups(self, virtual_machine_list, virtual_machine_id):
  virtual_machine = {}
  for x in virtual_machine_list:
    if x['uuid'] and x['uuid'] == virtual_machine_id:
      virtual_machine = x
  if not virtual_machine:
    raise ValueError(f'virtual machine with id {virtual_machine_id} not found')

  try:
    backup_list = json.loads(borg_core.borg_list_backup(virtual_machine['name']))
    return backup_list
  except Exception:
    self.retry(countdown=1)

@celery_app.task(name='List virtual machine disk(s)', bind=True)
def retrieve_virtual_machine_disk(self, virtual_machine_list, virtual_machine_id):
  try:
    virtual_machine = {}
    for x in virtual_machine_list:
      if x['uuid'] == virtual_machine_id:
        break
    virtual_machine = x
    data_host = jsonable_encoder(host.filter_host_by_id(virtual_machine['host']))
    virtual_machine_details = []
    virtual_machine_details = kvm_list_disk.getDisk(virtual_machine, data_host)
    return virtual_machine_details
  except Exception as e:
    raise HTTPException(status_code=500, detail=jsonable_encoder(e))

@app.get('/api/v1/virtualmachines/{virtual_machine_id}/breaklock', status_code=202)
def break_virtual_machine_borg_lock(virtual_machine_id, identity: Json = Depends(auth.valid_token)):
  if not virtual_machine_id: raise HTTPException(status_code=404, detail='Virtual machine not found')
  res = chain(host.retrieve_host.s(), dmap.s(parse_host.s()), handle_results.s(), borg_misc.borgbreaklock.s(virtual_machine_id)).apply_async()
  return {'Location': app.url_path_for('retrieve_task_status', task_id=res.id)}

@app.get('/api/v1/virtualmachines', status_code=202)
def list_virtual_machines(identity: Json = Depends(auth.valid_token)):
  # res = chain(host.retrieve_host.s(), chord((parse_host.s(host) for host in host_list))).apply_async()
  res = chain(host.retrieve_host.s(), dmap.s(parse_host.s()), handle_results.s()).apply_async()
  return {'Location': app.url_path_for('retrieve_task_status', task_id=res.id)}

@app.get('/api/v1/virtualmachines/{virtual_machine_id}', status_code=202)
def retrieve_specific_virtual_machine(virtual_machine_id, identity: Json = Depends(auth.valid_token)):
  if not virtual_machine_id: raise HTTPException(status_code=404, detail='Virtual machine not found')
  res = chain(host.retrieve_host.s(), dmap.s(parse_host.s()), handle_results.s(), retrieve_virtual_machine_disk.s(virtual_machine_id)).apply_async() 
  return {'Location': app.url_path_for('retrieve_task_status', task_id=res.id)}

@app.get('/api/v1/virtualmachines/{virtual_machine_id}/backups', status_code=202)
def retrieve_specific_virtual_machine_backups(virtual_machine_id, identity: Json = Depends(auth.valid_token)):
  if not virtual_machine_id: raise HTTPException(status_code=404, detail='Virtual machine not found')
  res = chain(host.retrieve_host.s(), dmap.s(parse_host.s()), handle_results.s(), retrieve_virtual_machine_backups.s(virtual_machine_id)).apply_async() 
  return {'Location': app.url_path_for('retrieve_task_status', task_id=res.id)}