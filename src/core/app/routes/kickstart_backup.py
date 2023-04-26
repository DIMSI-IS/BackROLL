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
from fastapi import HTTPException, Depends
from pydantic import Json
from celery_once import QueueOnce


from sqlmodel import Session, select
from app.kvm import kvm_manage_vm
from celery import chord

from app import app
from app import celery
from app import auth
from app import database
from app import task_handler

from app.backup_tasks import pool_backup
from app.database import Hosts

from app.routes import connectors
from app.routes import pool
from app.cloudstack import virtual_machine as cs_manage_vm

class connectorObject(object):
  pass

def getVMtobackup(pool_id):
  try:
    engine = database.init_db_connection()
  except Exception:
    raise
  virtual_machine_list = []
  try:
    with Session(engine) as session:
      statement = select(Hosts).where(Hosts.pool_id == pool_id)
      results = session.exec(statement)
      for host in results:
        HOST_UP  = True if os.system(f"nc -z -w 1 {host.ipaddress} 22 > /dev/null") == 0 else False
        if HOST_UP and host.ssh == 1:
          try:
            item_host = host.to_json()
            virtual_machine_list.extend(kvm_manage_vm.retrieve_virtualmachine(item_host))
          except Exception:
            raise
  except Exception:
    raise

  # Query VM list from powered and reachable hypervisors
  ready_to_backup_list = []
  for vm in virtual_machine_list:
    if vm['state'] == 'Running' and int(vm['id']) != -1:
      ready_to_backup_list.append(vm)

  # Check if pool has connector applied - if yes, retrieve powered off VM in cloudstack
  connector = connectors.filter_connector_by_id(pool.filter_pool_by_id(pool_id).connector_id)
  if connector:
    
    connector_obj = connectorObject()
    # Duplicate object connector to add pool_id property
    connector_obj.id = connector.id
    connector_obj.name = connector.name
    connector_obj.url = connector.url 
    connector_obj.login = connector.login
    connector_obj.password = connector.password
    connector_obj.pool_id = pool_id
    
    ready_to_backup_list += cs_manage_vm.listPoweredOffVms(connector_obj)

  print(ready_to_backup_list)

  return ready_to_backup_list

@celery.task(name='Kickstart_Pool_Backup', base=QueueOnce)
def kickstart_pool_backup(pool_id):
  try:
    ready_to_backup_list = getVMtobackup(pool_id)
    mychord = chord((pool_backup.backup_subtask.s(vm) for vm in ready_to_backup_list), task_handler.pool_backup_notification.s(pool_id))
    task = mychord.apply_async()
    return task.id
  except Exception:
    raise

@app.post('/api/v1/tasks/poolbackup/{pool_id}', status_code=202)
def start_pool_backup(pool_id, identity: Json = Depends(auth.valid_token)):
  try:
      uuid_obj = uuid_pkg.UUID(pool_id)
  except ValueError:
      raise HTTPException(status_code=404, detail='Given uuid is not valid')

  task_id = kickstart_pool_backup.delay(pool_id)

  return {'Location': app.url_path_for('retrieve_task_status', task_id=task_id)}