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
from pydantic import BaseModel, Json, field_validator
import requests
from requests.auth import HTTPBasicAuth
import json
from celery import chain

from typing import Optional

from app.initialized import fastapi_app, celery_app
from app.environment import get_flower_host
from app import task_history

from app.backup_tasks import single_backup

from app.routes import host
from app.routes import virtual_machine

from app import auth
from app import restore
from app import safety
from app import task_helper


class restorebackup_start(BaseModel):
    virtual_machine_id: str
    backup_name: str
    storage: Optional[str] = None
    mode: Optional[str] = None

    @field_validator("virtual_machine_id")
    @classmethod
    def check_machine(cls, value):
        UUID(value)
        return value

    @field_validator("backup_name")
    @classmethod
    def check_backup(cls, value):
        # The name ends in a shell command and in a path.
        if not safety.valid_backup_name(value):
            raise ValueError("Invalid backup name.")
        # The archives of folders and files are restored from the file browser, they are not disks.
        if value.startswith("files_"):
            raise ValueError("This is a backup of folders or files: it is not a disk and cannot be restored here.")
        return value

    class Config:
        schema_extra = {
            "example": {
                "virtual_machine_id": "3414b922-a39f-11ec-b909-0242ac120002",
                "backup_name": "vda_VMDiskName_01092842912",
                "storage": "path",
                "mode": "simple"
            }
        }


def get_task_logs(task_id):
    response = requests.get(
        f'http://{get_flower_host()}:5555/api/task/info/{task_id}', timeout=20)
    return response.content


@fastapi_app.get('/api/v1/status/{task_id}', status_code=200)
def retrieve_task_status(task_id, identity: Json = Depends(auth.verify_token)):
    try:
        uuid_obj = UUID(task_id)
    except ValueError:
        raise HTTPException(status_code=404, detail='Given uuid is not valid')
    task = celery_app.AsyncResult(task_id)
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
            'status': 'In progress...',
            # The step reached, when the task reports it.
            'info': task.info if isinstance(task.info, dict) else None
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
        if "not found" in str(task.info):
            raise HTTPException(status_code=404, detail=response)
        else:
            raise HTTPException(status_code=500, detail=response)
    return response


@fastapi_app.get('/api/v1/logs/{task_id}', status_code=200)
def retrieve_task_logs(task_id, identity: Json = Depends(auth.verify_token)):
    try:
        uuid_obj = UUID(task_id)
    except ValueError:
        raise HTTPException(status_code=404, detail='Given uuid is not valid')
    return get_task_logs(task_id)


@fastapi_app.post('/api/v1/tasks/singlebackup/{virtual_machine_id}', status_code=202)
def start_vm_single_backup(virtual_machine_id, identity: Json = Depends(auth.require_editor)):
    try:
        uuid_obj = UUID(virtual_machine_id)
    except ValueError:
        raise HTTPException(status_code=404, detail='Given uuid is not valid')
    if not virtual_machine_id:
        raise HTTPException(
            status_code=404, detail='Virtual machine not found')
    res = chain(host.retrieve_host.s(), virtual_machine.dmap.s(virtual_machine.parse_host.s()), virtual_machine.handle_results.s(
    ), virtual_machine.filter_virtual_machine_list.s(virtual_machine_id), single_backup.single_vm_backup.s()).apply_async()
    return {'Location': fastapi_app.url_path_for('retrieve_task_status', task_id=res.id)}


@fastapi_app.post('/api/v1/tasks/restore/{virtual_machine_id}', status_code=202)
def start_vm_restore(virtual_machine_id, item: restorebackup_start, identity: Json = Depends(auth.require_editor)):
    try:
        uuid_obj = UUID(virtual_machine_id)
    except ValueError:
        raise HTTPException(status_code=404, detail='Given uuid is not valid')
    # The machine of the address is the machine in the body: the audit log must name the one that is restored.
    if UUID(item.virtual_machine_id) != uuid_obj:
        raise HTTPException(status_code=422, detail='The virtual machine of the request does not match its address.')
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
    return {'Location': fastapi_app.url_path_for('retrieve_task_status', task_id=res.id)}


def flower_tasks(task_name):
    """The tasks Flower knows. Without Flower, only the history of the database is shown."""
    try:
        response = requests.get(
            f'http://{get_flower_host()}:5555/api/tasks', params={"taskname": task_name}, timeout=20)
        return json.loads(response.content.decode('ascii'))
    except (requests.RequestException, ValueError):
        return {}


@celery_app.task(name='restore_task_jobs')
def retrieve_restore_task_jobs():
    single_vm_task = flower_tasks("VM_Restore_Disk")

    task_helper.manage_task_dict_args(single_vm_task)

    return task_history.merge(single_vm_task, task_history.RESTORE_TASKS)


@celery_app.task(name='backuptask_jobs')
def retrieve_backup_task_jobs():
    aggregated_jobs_list = flower_tasks("Single_VM_Backup")
    aggregated_jobs_list.update(flower_tasks("Pool_VM_Backup"))
    aggregated_jobs_list.update(flower_tasks("backup_subtask"))

    task_helper.manage_task_dict_args(aggregated_jobs_list)

    return task_history.merge(aggregated_jobs_list, task_history.BACKUP_TASKS)


@fastapi_app.get('/api/v1/tasks/backup', status_code=200)
def list_backup_tasks(identity: Json = Depends(auth.verify_token)):
    return {'info': retrieve_backup_task_jobs()}


@fastapi_app.get('/api/v1/tasks/restore', status_code=200)
def list_restore_tasks(identity: Json = Depends(auth.verify_token)):
    return {'info': retrieve_restore_task_jobs()}
