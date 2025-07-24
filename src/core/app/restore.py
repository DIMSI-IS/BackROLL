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
import json
import os
import shutil
import subprocess
from redis import Redis
from fastapi.encoders import jsonable_encoder
from celery_once import QueueOnce
from app.initialized import celery_app

from app.routes import host
from app.routes import storage
from app.kvm import kvm_list_disk
from app.cloudstack import virtual_machine as cs_vm_command

from app.routes import pool
from app.routes import connectors

from app.patch import make_path
from app import shell

# KVM custom module import
from app.kvm import kvm_manage_vm

# CS custom module import
from app.cloudstack import virtual_machine as cs_manage_vm


@celery_app.task(name='VM_Restore_Disk', bind=True, max_retries=3, base=QueueOnce)
def restore_disk_vm(self, info, backup_name, storage, mode):
    # def restore_disk_vm(self, info, backup_name):

    if not info:
        raise Exception("Virtual machine not found to process restore")
    # mode = "single"
    # storage = "test"
    print("DEBUG $$$ vm uuid: " + info["uuid"])
    for x in info:
        print(x)

    redis_client = Redis(host='localhost', port=6379)
    try:
        vm_lock_key = f'vmlock-{info}'
        if not redis_client.exists(vm_lock_key):
            # No duplicated key found in redis - target IS NOT locked right now
            redis_client.set(vm_lock_key, "")
            try:
                redis_client.expire(vm_lock_key, 5400)

                if "host" in info:
                    # Retrieve VM host info
                    host_info = jsonable_encoder(
                        host.filter_host_by_id(info['host']))
                    vm_storage_info = kvm_list_disk.getDisk(info, host_info)
                else:
                    print("DEBUG POOL ID")
                    host_info = None
                    connector = connectors.filter_connector_by_id(
                        pool.filter_pool_by_id(info["pool_id"]).connector_id)
                    vm_storage_info = cs_manage_vm.getDisk(connector, info)

                if mode == "mounted":
                    try:
                        print("Debug - go to restore_to_path_task")
                        restore_to_path_task(
                            self, info, host_info, storage, backup_name)
                    except Exception:
                        self.retry(countdown=3**self.request.retries)
                else:
                    try:
                        print("Debug - go to restore_task")
                        restore_task(self, info, host_info,
                                     vm_storage_info, backup_name)
                    except Exception:
                        raise
                        # self.retry(countdown=3**self.request.retries)
            finally:
                redis_client.delete(vm_lock_key)
        else:
            # Duplicated key found in redis - target IS locked right now
            raise ValueError("This task is already running / scheduled")
    finally:
        redis_client.quit()

# def restore_task(self, info, hypervisor, disk_list, backup):


def is_nfs(path):
    result = shell.subprocess_run(f'df -T {path}')
    lines = result.strip().split('\n')

    if len(lines) < 2:
        return False

    cols = lines[1].split()
    if len(cols) < 2:
        return False

    type_fs = cols[1].lower()
    return type_fs in ('nfs', 'nfs4')


def restore_task(self, virtual_machine_info, hypervisor, vm_storage_info, backup_name):
    print("Debug - restore_task - start")
    vm_storage = storage.retrieveStoragePathFromHostBackupPolicy(
        virtual_machine_info)
    borg_repository = vm_storage["path"]
    print("DEBUG borg_repository " + borg_repository)

    restore_path = make_path(borg_repository, "restore",
                             virtual_machine_info['name'], directory=True)

    try:

        disk_device = backup_name.split('_')[0]

        # Remove existing files inside restore folder
        shell.subprocess_run(f"rm -rf {restore_path}")

        # Create temporary folder to extract borg archive
        shell.subprocess_run(f"mkdir -p {restore_path}")

        # Go into directory
        os.chdir(restore_path)

        connector = None
        pool_id = None

        if "pool_id" in virtual_machine_info:
            pool_id = virtual_machine_info["pool_id"]
        else:
            pool_id = hypervisor["pool_id"]

        connector_id = pool.filter_pool_by_id(pool_id).connector_id
        if connector_id:
            connector = connectors.filter_connector_by_id(connector_id)
        elif virtual_machine_info['cloudstack_instance']:
            raise ValueError('You have to add a CloudStack connector.')

        try:
            # Extract selected borg archive
            # Local backup storage does not support extended attributes nor ACLs. NFS does.
            # TODO Consider extracting the backup next to the archive source so that it will be on the same filesystem
            # — not on the backup storage.
            shell.subprocess_popen(
                f"""borg extract --sparse \
                    {"" if is_nfs(restore_path) else "--noxattrs --noacls"} \
                    {make_path(borg_repository, virtual_machine_info['name'])}::{backup_name}""")

            # Skip directories
            shell.os_system('mv $(find -type f) ./')

            # Loop through VM's disks to find filedisk
            for disk in vm_storage_info:
                if disk['device'] == disk_device:
                    break
            virtual_machine_disk = disk["source"]

            # Build path based on disk source path
            if "host" in virtual_machine_info:
                # For a KVM vm
                kvm_storagepath = make_path(
                    *list(filter(None, virtual_machine_disk.split("/")))[:-1], rooted=True, directory=True)
            else:
                # For a powered off CS vm
                kvm_storagepath = make_path(
                    "/mnt", cs_manage_vm.listStorage(connector, disk)["id"], directory=True)

            if virtual_machine_disk == None:
                raise ValueError(
                    'Unable to match backup with existing diskfile. Aborting restore job')

            if "host" in virtual_machine_info:
                virtual_machine_diskName = virtual_machine_disk.split('/')[-1]
            else:
                virtual_machine_diskName = disk["path"]

            if "host" in virtual_machine_info:
                # Power off guest VM
                if connector_id:
                    cs_vm_command.stop_vm(
                        connector, virtual_machine_info['uuid'])
                else:
                    kvm_manage_vm.stop_vm(virtual_machine_info, hypervisor)

            try:

                kvm_storage_disk_path = make_path(
                    kvm_storagepath, virtual_machine_diskName)
                kvm_storage_disk_path_tmp = f"{kvm_storage_disk_path}.tmp"

                # subprocess.run(['cp', virtual_machine_diskName, kvm_storage_disk_path_tmp], check = True)
                shell.os_system(
                    f"cp {virtual_machine_diskName} {kvm_storage_disk_path_tmp}")

                # Fix permissions of new qcow2 filedisk
                # subprocess.run(['chmod', '644', kvm_storage_disk_path_tmp], check = True)
                shell.os_system(f"chmod 644 {kvm_storage_disk_path_tmp}")

                # Replace disk by extracted backup
                # subprocess.run(['mv', kvm_storage_disk_path_tmp, kvm_storage_disk_path], check = True)
                shell.os_system(
                    f"mv {kvm_storage_disk_path_tmp} {kvm_storage_disk_path}")

                # Remove temporary folder used to extract borg archive
                # subprocess.run(['rm', "-rf", restore_path])
                shell.os_system(f"rm -rf {restore_path}")
            except Exception as e:
                raise e

            if "host" in virtual_machine_info:
                # Power on guest VM
                if connector_id:
                    cs_vm_command.start_vm(
                        connector, virtual_machine_info['uuid'])
                else:
                    kvm_manage_vm.start_vm(virtual_machine_info, hypervisor)

        except Exception as e:
            # Remove restore artifacts
            shell.subprocess_run(f"rm -rf {restore_path}")
            raise e
        print("Debug - restore_task - end")
    except Exception as e:

        # Remove restore artifacts
        try:
            shell.subprocess_run(f"rm -rf {restore_path}")
        except Exception as err:
            print(err)

        raise e


@celery_app.task(name='VM_Restore_To_Path', bind=True, max_retries=3, base=QueueOnce)
# TODO Fixme but referenced in the code.
def restore_to_path_task(self, virtual_machine_info, backup_name, storage_path, mode):
    """Deactivated task but referenced in the code. Mind code factorization and code duplication when re-opening the feature development."""

    print("restore_to_path_task")
    print("storage: " + storage_path)
    print("backup: " + backup_name)
    virtual_machine_path = virtual_machine_info
    # TODO use make_path
    virtual_machine_complete_path = virtual_machine_info + "/"
    print("virtual_machine_path: " + virtual_machine_path)
    virtual_machine_name = os.path.basename(
        os.path.dirname(virtual_machine_complete_path))
    print("virtual_machine_name: " + virtual_machine_name)

    try:
        # Remove existing files inside restore folder
        shell.subprocess_run(
            f"rm -rf {storage_path}/restore/{virtual_machine_name}")

        # Create temporary folder to extract borg archive
        shell.subprocess_run(
            f"mkdir -p {storage_path}/restore/{virtual_machine_name}")

        # Go into directory
        os.chdir(f"{storage_path}/restore/{virtual_machine_name}")

        # TODO Group common code and mind depth independent restore.
        shell.subprocess_popen(
            f"""borg extract --sparse --strip-components=2 {virtual_machine_path}::{backup_name}""")

        diskList = shell.os_popen("ls").split('\n')
        disk = diskList[0]
        print("Disk: " + disk)
        storageList = storage.retrieve_storage()
        repository = storageList[1]["path"]
        print("repo : " + repository)
        json_output = shell.subprocess_run(
            f"qemu-img info --output=json {disk}")
        qemu_img_info = json.loads(json_output)
        if qemu_img_info.get('full-backing-filename'):
            print(
                f'[{virtual_machine_name}] Checking that {virtual_machine_name}\'s backing file has already been backed up')
            backing_file = qemu_img_info['full-backing-filename'].split(
                '/')[-1]
            print("backing file: " + backing_file)

            shutil.copy(f"{repository}template/{backing_file}",
                        f"{storage_path}/restore/{backing_file}")
            print(
                f'[{virtual_machine_name}] Backing up the backing file has successfully completed')

            # rebase
            dst = f"{storage_path}/restore/{backing_file}"
            print("dst: " + dst)
            print("disk: " + disk)
            cmd = f"qemu-img rebase -f qcow2 -u -b {dst} {disk}"
            print("cmd: " + cmd)
            # rebaseRequest = subprocess.run(["qemu-img ", "rebase", "-f qcow2", "-u", "-b", dst, disk, "--output=json"], capture_output=True)
            # rebaseRequest = subprocess.run(cmd, capture_output=True)
            # rebaseRequest = subprocess.run([cmd], capture_output=True)
            # qemu_img_rebase = rebaseRequest.stdout.decode("utf-8")
            # qemu_img_rebase = json.loads(qemu_img_rebase)
            shell.os_popen(cmd).split('\n')
            print("end rebase")

            # qemu info to check the rebase
            json_output = shell.subprocess_run(
                f"qemu-img info --output=json {disk}")
            qemu_img_info = json.loads(json_output)
            # check if ok
            print("end info")

            # qemu commit
            cmd = f"qemu-img commit -f qcow2 {disk}"
            # commitRequest = subprocess.run(["qemu-img ", "commit", "-f qcow2", "--output=json", disk], capture_output=True)
            # qemu_img_commit = commitRequest.stdout.decode("utf-8")
            # qemu_img_commit = json.loads(qemu_img_commit)
            shell.os_popen(cmd).split('\n')
            print("end commit")

            # rename backring file
            os.rename(f"{storage_path}/restore/{backing_file}",
                      f"{storage_path}/restore/restore_{virtual_machine_name}")

            # Remove restore artifacts
            try:
                shell.subprocess_run(
                    f"rm -rf {storage_path}/restore/{virtual_machine_name}")
            except Exception as err:
                print(err)
                raise err
    except Exception as e:
        raise e
