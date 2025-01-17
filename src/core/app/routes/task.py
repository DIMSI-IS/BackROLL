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

#!/usr/bin/env python
import os
import sys
import logging
from uuid import UUID
from fastapi import HTTPException, Depends
from pydantic import BaseModel, Json
import requests
from requests.auth import HTTPBasicAuth
import json

from typing import Optional

from app import app
from app import celery
from celery import chain

from app.backup_tasks import single_backup

from app.routes import host
from app.routes import virtual_machine

from app import task_handler

from app import auth
from app import restore


class restorebackup_start(BaseModel):
    virtual_machine_id: str
    backup_name: str
    storage: Optional[str] = None
    mode: Optional[str] = None

    class Config:
        schema_extra = {
            "example": {
                "virtual_machine_id": "3414b922-a39f-11ec-b909-0242ac120002",
                "backup_name": "vda_VMDiskName_01092842912",
                "storage": "path",
                "mode": "simple"
            }
        }


@celery.task(name='restore_task_jobs')
def retrieve_restore_task_jobs():
    single_vm_payload = {"taskname": "VM_Restore_Disk"}
    single_vm_response = requests.get(
        'http://flower:5555/api/tasks', params=single_vm_payload)
    single_vm_task = json.loads(single_vm_response.content.decode('ascii'))
    for key in single_vm_task:
        json_key = single_vm_task[key]
        json_key["args"] = json.dumps(
            task_handler.parse_task_args(json_key["args"]))

    vm_retore_path_payload = {"taskname": "VM_Restore_To_Path"}
    vm_retore_path_response = requests.get(
        'http://flower:5555/api/tasks', params=vm_retore_path_payload)
    vm_retore_path_task = json.loads(
        vm_retore_path_response.content.decode('ascii'))
    for key in vm_retore_path_task:
        json_key = vm_retore_path_task[key]
        json_key["args"] = json.dumps(
            task_handler.parse_task_args(json_key["args"]))

    single_vm_task.update(vm_retore_path_task)
    return single_vm_task


@celery.task(name='backuptask_jobs')
def retrieve_backup_task_jobs():
    single_vm_payload = {"taskname": "	Single_VM_Backup"}
    single_vm_response = requests.get(
        'http://flower:5555/api/tasks', params=single_vm_payload)
    pool_payload = {"taskname": "Pool_VM_Backup"}
    pool_response = requests.get(
        'http://flower:5555/api/tasks', params=pool_payload)
    subtask_payload = {"taskname": "backup_subtask"}
    subtask_response = requests.get(
        'http://flower:5555/api/tasks', params=subtask_payload)
    single_vm_task = json.loads(single_vm_response.content.decode('ascii'))
    pool_vm_task = json.loads(pool_response.content.decode('ascii'))
    subtask = json.loads(subtask_response.content.decode('ascii'))
    aggregated_jobs_list = single_vm_task.copy()
    aggregated_jobs_list.update(pool_vm_task)
    aggregated_jobs_list.update(subtask)
    for key in aggregated_jobs_list:
        json_key = aggregated_jobs_list[key]
        json_key["args"] = json.dumps(
            task_handler.parse_task_args(json_key["args"]))
    return aggregated_jobs_list


def get_task_logs(task_id):
    response = requests.get(f'http://flower:5555/api/task/info/{task_id}')
    return response.content


@app.get('/api/v1/status/{task_id}', status_code=200)
def retrieve_task_status(task_id, identity: Json = Depends(auth.valid_token)):
    try:
        uuid_obj = UUID(task_id)
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
    elif task.state == 'PROGRESS':
        response = {
            'state': task.state,
            'status': 'In progress...'
        }
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
        # if "not found" in str(task.info):
        #     raise HTTPException(status_code=404, detail=response)
        # else:
        #     raise HTTPException(status_code=500, detail=response)
    return response


@app.get('/api/v1/logs/{task_id}', status_code=200)
def retrieve_task_logs(task_id, identity: Json = Depends(auth.valid_token)):
    try:
        uuid_obj = UUID(task_id)
    except ValueError:
        raise HTTPException(status_code=404, detail='Given uuid is not valid')
    return get_task_logs(task_id)


@app.post('/api/v1/tasks/singlebackup/{virtual_machine_id}', status_code=202)
def start_vm_single_backup(virtual_machine_id, identity: Json = Depends(auth.valid_token)):
    try:
        uuid_obj = UUID(virtual_machine_id)
    except ValueError:
        raise HTTPException(status_code=404, detail='Given uuid is not valid')
    if not virtual_machine_id:
        raise HTTPException(
            status_code=404, detail='Virtual machine not found')
    res = chain(host.retrieve_host.s(), virtual_machine.dmap.s(virtual_machine.parse_host.s()), virtual_machine.handle_results.s(
    ), virtual_machine.filter_virtual_machine_list.s(virtual_machine_id), single_backup.single_vm_backup.s()).apply_async()
    return {'Location': app.url_path_for('retrieve_task_status', task_id=res.id)}


@app.post('/api/v1/tasks/restore/{virtual_machine_id}', status_code=202)
def start_vm_restore(virtual_machine_id, item: restorebackup_start, identity: Json = Depends(auth.valid_token)):
    try:
        uuid_obj = UUID(virtual_machine_id)
    except ValueError:
        raise HTTPException(status_code=404, detail='Given uuid is not valid')
    virtual_machine_id = item.virtual_machine_id
    print("DEBUG ID VM : " + virtual_machine_id)
    # print("virtual_machine_id: " + virtual_machine_id)
    backup_name = item.backup_name
    # print("backup_name: " + backup_name)
    # storage = item.storage
    # print("storage: " + storage)
    # mode = item.mode
    # print("mode: " + mode)
    print(uuid_obj)
    res = chain(host.retrieve_host.s(), virtual_machine.dmap.s(virtual_machine.parse_host.s()), virtual_machine.handle_results.s(
    ), virtual_machine.filter_virtual_machine_list.s(virtual_machine_id), restore.restore_disk_vm.s(backup_name, '', '')).apply_async()
    # res = chain(host.retrieve_host.s(), virtual_machine.dmap.s(virtual_machine.parse_host.s()), virtual_machine.handle_results.s(), virtual_machine.filter_virtual_machine_list.s(virtual_machine_id), restore.restore_disk_vm.s(backup_name)).apply_async()
    return {'Location': app.url_path_for('retrieve_task_status', task_id=res.id)}


@app.post('/api/v1/tasks/restorespecificpath', status_code=202)
def start_vm_restore_specific_path(item: restorebackup_start, identity: Json = Depends(auth.valid_token)):
    virtual_machine_id = item.virtual_machine_id
    backup_name = item.backup_name
    storage = item.storage
    mode = item.mode
    # res = chain(host.retrieve_host.s(), virtual_machine.dmap.s(virtual_machine.parse_host.s()), virtual_machine.handle_results.s(), virtual_machine.filter_virtual_machine_list.s(virtual_machine_id), restore.restore_disk_vm.s(backup_name, storage, mode)).apply_async()
    # res = chain(host.retrieve_host.s(), virtual_machine.dmap.s(virtual_machine.parse_host.s()), virtual_machine.handle_results.s(), virtual_machine.filter_virtual_machine_list.s(virtual_machine_id), restore.restore_disk_vm.s(backup_name)).apply_async()
    res = chain(restore.restore_to_path_task.s(
        virtual_machine_id, backup_name, storage, mode)).apply_async()
    return {'Location': app.url_path_for('retrieve_task_status', task_id=res.id)}


@app.get('/api/v1/tasks/backup', status_code=200)
def list_backup_tasks(identity: Json = Depends(auth.valid_token)):
    return {'info': retrieve_backup_task_jobs()}


@app.get('/api/v1/tasks/restore', status_code=200)
def list_restore_tasks(identity: Json = Depends(auth.valid_token)):
    return {'info': retrieve_restore_task_jobs()}
