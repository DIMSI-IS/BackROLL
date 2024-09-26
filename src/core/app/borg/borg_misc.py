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
from os import path

import subprocess

from app import app
from app import celery
from app.routes import storage
from app.patch import make_path


def borglock(payload):
    borgbreaklock.delay(payload)


@celery.task(name='Break BORG repository lock')
def borgbreaklock(virtual_machine_list, virtual_machine_id):
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
        repository = vm_storage["path"]
        vm_repository = make_path(repository, virtual_machine["name"])
        if not path.isdir(vm_repository):
            raise ValueError(
                f'Borg repository not found for virtual machine with {virtual_machine_id}')

        command = f'borg break-lock {vm_repository}'
        subprocess.run(command.split(), check=True)
    except Exception as e:
        raise ValueError(e)
