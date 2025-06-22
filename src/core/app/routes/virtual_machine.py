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
from fastapi import HTTPException, Depends
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Json

from celery.result import allow_join_result
from celery import subtask, group, chain

import json
import re

from app.initialized import fastapi_app
from app.initialized import celery_app as celery_app

from app import auth

from app.borg import borg_core
from app.borg import borg_misc

from app.routes import pool
from app.routes import host
from app.routes import connectors
from app.routes import storage

from app.backup_tasks import manage_backup

from app.patch import make_path
from app.virtual_machine_helper import add_disk_access_check
from app import shell

# CS Imports
from app.cloudstack import virtual_machine as cs_manage_vm

# KVM Imports
from app.kvm import kvm_manage_vm
from app.kvm import kvm_list_disk

import os


class connectorObject(object):
    pass


class VirtualMachineStorage:
    def __init__(self, name, path):
        self.name = name
        self.path = path


class VirtualMachineBackupsRequest(BaseModel):
    virtualMachineName: str
    storagePath: str


@celery_app.task(name='Filter VMs list')
def filter_virtual_machine_list(virtual_machine_list, virtual_machine_id):
    print(virtual_machine_id)
    vmToFind = {}
    for vm in virtual_machine_list:
        print(vm['uuid'])
        if vm['uuid'] == virtual_machine_id:
            vmToFind = vm
    return vmToFind


@celery_app.task(name='Parse Host instance(s)')
def parse_host(host):
    if host['state'] == 'Reachable' and host['ssh'] == 1:
        return {"host": host, "virtualmachines": kvm_manage_vm.retrieve_virtualmachine(host)}
    else:
        return {"host": host, "virtualmachines": []}


@celery_app.task
def dmap(it, callback):
    # Map a callback over an iterator and return as a group
    callback = subtask(callback)
    c = group(callback.clone([arg,]) for arg in it)()
    c.save()
    return c.id


@celery_app.task
def handle_results(group_id):
    # Setting up variables
    pool_set = set()
    connector_list = []
    cs_vm_list = []

    # This part merge all hypervisors results into one global virtual machines list
    with allow_join_result():
        restored_group_result = celery_app.GroupResult.restore(group_id)
        result = restored_group_result.get()
    global_instance_list = []
    for instance_list in result:
        pool_set.add(instance_list["host"]["pool_id"])
        if instance_list["virtualmachines"]:
            global_instance_list += instance_list["virtualmachines"]
    # This part is dedicated to retrieve VM using host related connectors (AKA Cloudstack discovery)
    for pool_id in pool_set:
        connector_id = pool.filter_pool_by_id(pool_id).connector_id
        # if connector_id is not null, we need to retrieve connector object
        if connector_id:
            connector = connectors.filter_connector_by_id(connector_id)
            if connector not in connector_list:
                connector_obj = connectorObject()
                # Duplicate object connector to add pool_id property
                connector_obj.id = connector.id
                connector_obj.name = connector.name
                connector_obj.url = connector.url
                connector_obj.login = connector.login
                connector_obj.password = connector.password
                connector_obj.pool_id = pool_id
                connector_list.append(connector_obj)
    for connector in connector_list:
        cs_vm_list += cs_manage_vm.listAllVms(connector)

    # Merge KVM and CS discovered virtual machines to a single array

    for vm in cs_vm_list:
        if not any(x['uuid'] == vm['uuid'] for x in global_instance_list):
            global_instance_list.append(vm)

    return global_instance_list


@celery_app.task(name='List VMs backups', bind=True, max_retries=3)
def retrieve_virtual_machine_backups(self, virtual_machine_list, virtual_machine_id):
    virtual_machine = {}
    for x in virtual_machine_list:
        if 'uuid' in x:
            if x['uuid'] == virtual_machine_id:
                virtual_machine = x
    if not virtual_machine:
        raise ValueError(
            f'virtual machine with id {virtual_machine_id} not found')

    try:
        vm_storage = storage.retrieveStoragePathFromHostBackupPolicy(
            virtual_machine)
        backup_list = json.loads(borg_core.borg_list_backup(
            virtual_machine['name'], vm_storage["path"]))
        return backup_list
    except Exception:
        self.retry(countdown=1)


@celery_app.task(name='List VM repository', bind=True, max_retries=3)
def retrieve_virtual_machine_repository(self, virtual_machine_list, virtual_machine_id):
    virtual_machine = {}
    for x in virtual_machine_list:
        if 'uuid' in x:
            if x['uuid'] == virtual_machine_id:
                virtual_machine = x
    if not virtual_machine:
        raise ValueError(
            f'virtual machine with id {virtual_machine_id} not found')

    try:
        vm_storage = storage.retrieveStoragePathFromHostBackupPolicy(
            virtual_machine)
        backup_list = json.loads(borg_core.borg_list_repository(
            virtual_machine['name'], vm_storage["path"]))
        return backup_list
    except Exception:
        self.retry(countdown=1)


@celery_app.task(name='Get VM backup stats', bind=True, max_retries=3)
def retrieve_virtual_machine_backup_stats(self, virtual_machine_list, virtual_machine_id, backup_name):
    virtual_machine = {}
    for x in virtual_machine_list:
        if x['uuid'] and x['uuid'] == virtual_machine_id:
            virtual_machine = x
    if not virtual_machine:
        raise ValueError(
            f'virtual machine with id {virtual_machine_id} not found')

    try:
        vm_storage = storage.retrieveStoragePathFromHostBackupPolicy(
            virtual_machine)
        backup_stats = borg_core.borg_backup_info(
            virtual_machine['name'], vm_storage["path"], backup_name)
        return backup_stats
    except Exception:
        self.retry(countdown=1)


@celery_app.task(name='List virtual machine disk(s)', bind=True)
def retrieve_virtual_machine_disk(self, virtual_machine_list, virtual_machine_id):
    try:
        for vm in virtual_machine_list:
            if vm['uuid'] == virtual_machine_id:
                break
        virtual_machine = vm

        if 'host' in virtual_machine:
            data_host = jsonable_encoder(
                host.filter_host_by_id(virtual_machine['host']))
            virtual_machine['storage'] = kvm_list_disk.getDisk(
                virtual_machine, data_host)
        else:
            connector = connectors.filter_connector_by_id(
                pool.filter_pool_by_id(virtual_machine["pool_id"]).connector_id)
            virtual_machine['storage'] = cs_manage_vm.getDisk(
                connector, virtual_machine)
            for disk in virtual_machine['storage']:
                disk["source"] = make_path(
                    "/mnt", cs_manage_vm.listStorage(connector, disk)["id"], disk["source"])

        add_disk_access_check(virtual_machine)

        return virtual_machine
    except Exception as e:
        raise ValueError(e)


@celery_app.task(name='List virtual machines folders', bind=True, max_retries=3)
def retrieve_virtual_machine_paths(self):
    try:
        storagePaths = []
        storagePathsFromDb = storage.retrieveStoragePathsFromDb()
        print(storagePathsFromDb)
        for path in storagePathsFromDb:
            subFolders = os.scandir(path.path)
            for subFolder in subFolders:
                # TODO ux-paths ?
                configFilePath = subFolder.path + "/config"
                print("configFilePath _______ " + configFilePath)
                if os.path.exists(configFilePath):
                    storagePaths.append(VirtualMachineStorage(
                        subFolder.name, subFolder.path))
        return storagePaths

    except Exception as e:
        self.retry(countdown=1)
        raise ValueError(e)


@celery_app.task(name='List virtual machine backups', bind=True)
def retrieve_virtual_machine_backups_from_path(self, virtualMachineName: str, storagePath: str):
    try:
        backup_list = json.loads(borg_core.borg_list_backup(
            virtualMachineName, storagePath))
        return backup_list

    except Exception as e:
        raise ValueError(e)


@fastapi_app.get('/api/v1/virtualmachines/{virtual_machine_id}/breaklock', status_code=202)
def break_virtual_machine_borg_lock(virtual_machine_id, identity: Json = Depends(auth.verify_token)):
    if not virtual_machine_id:
        raise HTTPException(
            status_code=404, detail='Virtual machine not found')
    res = chain(host.retrieve_host.s(), dmap.s(parse_host.s()), handle_results.s(
    ), borg_misc.borgbreaklock.s(virtual_machine_id)).apply_async()
    return {'Location': fastapi_app.url_path_for('retrieve_task_status', task_id=res.id)}


@fastapi_app.get('/api/v1/virtualmachines', status_code=202)
def list_virtual_machines(identity: Json = Depends(auth.verify_token)):
    res = chain(host.retrieve_host.s(), dmap.s(
        parse_host.s()), handle_results.s()).apply_async()
    return {'Location': fastapi_app.url_path_for('retrieve_task_status', task_id=res.id)}


@fastapi_app.get('/api/v1/virtualmachines/{virtual_machine_id}', status_code=202)
def retrieve_specific_virtual_machine(virtual_machine_id, identity: Json = Depends(auth.verify_token)):
    if not virtual_machine_id:
        raise HTTPException(
            status_code=404, detail='Virtual machine not found')
    res = chain(host.retrieve_host.s(), dmap.s(parse_host.s()), handle_results.s(
    ), retrieve_virtual_machine_disk.s(virtual_machine_id)).apply_async()
    return {'Location': fastapi_app.url_path_for('retrieve_task_status', task_id=res.id)}


@fastapi_app.get('/api/v1/virtualmachines/{virtual_machine_id}/backups', status_code=202)
def list_virtual_machine_backups(virtual_machine_id, identity: Json = Depends(auth.verify_token)):
    if not virtual_machine_id:
        raise HTTPException(
            status_code=404, detail='Virtual machine not found')
    res = chain(host.retrieve_host.s(), dmap.s(parse_host.s()), handle_results.s(
    ), retrieve_virtual_machine_backups.s(virtual_machine_id)).apply_async()
    return {'Location': fastapi_app.url_path_for('retrieve_task_status', task_id=res.id)}


@fastapi_app.delete('/api/v1/virtualmachines/{virtual_machine_id}/backups/{backup_name}', status_code=202)
def delete_specific_virtual_machine_backup(virtual_machine_id, backup_name, identity: Json = Depends(auth.verify_token)):
    if not virtual_machine_id:
        raise HTTPException(
            status_code=404, detail='Virtual machine not found')
    if not backup_name:
        raise HTTPException(status_code=404, detail='Backup not found')
    res = chain(host.retrieve_host.s(), dmap.s(parse_host.s()), handle_results.s(
    ), manage_backup.remove_archive.s(virtual_machine_id, backup_name)).apply_async()
    return {'Location': fastapi_app.url_path_for('retrieve_task_status', task_id=res.id)}


@fastapi_app.get('/api/v1/virtualmachines/{virtual_machine_id}/repository', status_code=202)
def list_virtual_machine_repository(virtual_machine_id, identity: Json = Depends(auth.verify_token)):
    if not virtual_machine_id:
        raise HTTPException(
            status_code=404, detail='Virtual machine not found')
    res = chain(host.retrieve_host.s(), dmap.s(parse_host.s()), handle_results.s(
    ), retrieve_virtual_machine_repository.s(virtual_machine_id)).apply_async()
    return {'Location': fastapi_app.url_path_for('retrieve_task_status', task_id=res.id)}


@fastapi_app.get('/api/v1/virtualmachines/{virtual_machine_id}/backups/{backup_name}', status_code=202)
def get_virtual_machine_backup_stats(virtual_machine_id, backup_name, identity: Json = Depends(auth.verify_token)):
    if not virtual_machine_id:
        raise HTTPException(
            status_code=404, detail='Virtual machine not found')
    res = chain(host.retrieve_host.s(), dmap.s(parse_host.s()), handle_results.s(
    ), retrieve_virtual_machine_backup_stats.s(virtual_machine_id, backup_name)).apply_async()
    return {'Location': fastapi_app.url_path_for('retrieve_task_status', task_id=res.id)}


@fastapi_app.get('/api/v1/virtualmachinespaths', status_code=202)
def get_virtual_machine_paths(identity: Json = Depends(auth.verify_token)):
    return {'paths': retrieve_virtual_machine_paths()}


@fastapi_app.post('/api/v1/virtualmachinebackupsfrompath', status_code=202)
def get_virtual_machine_backups_from_path(virtualMachineBackupsRequest: VirtualMachineBackupsRequest, identity: Json = Depends(auth.verify_token)):
    res = chain(retrieve_virtual_machine_backups_from_path.s(
        virtualMachineBackupsRequest.virtualMachineName, virtualMachineBackupsRequest.storagePath)).apply_async()
    return {'Location': fastapi_app.url_path_for('retrieve_task_status', task_id=res.id)}
