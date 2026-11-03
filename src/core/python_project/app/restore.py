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
import shlex
import subprocess
from pathlib import Path
from fastapi.encoders import jsonable_encoder
from celery_once import QueueOnce

from app.initialized import celery_app
from app.redis import new_redis_client

from app.routes import host
from app.routes import storage
from app.kvm import kvm_list_disk
from app.cloudstack import virtual_machine as cs_vm_command

from app.routes import pool
from app.routes import connectors

from app.patch import make_path
from app import backup_limit, file_browser, safety, shell

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

    redis_client = new_redis_client()
    try:
        # TODO Duplicated code ?
        # The lock of the backups: a restore does not start during a backup of the machine, nor a backup during it.
        vm_lock_key = backup_limit.acquire_vm_lock(redis_client, info)
        if vm_lock_key is not None:
            # The machine was not locked: it is now
            try:
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


def extracted_size(name):
    """What the extracted disk takes on the disk (a sparse file takes less than its size), 0 when unknown."""
    try:
        return os.stat(name).st_blocks * 512
    except (OSError, AttributeError):
        return 0


def check_room_to_replace(directory, needed):
    probe = Path(directory)
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    free = shutil.disk_usage(probe).free
    if free < needed:
        raise ValueError(
            f"Not enough free space where the disk is replaced ({probe}): it needs about {needed // 1024 ** 2} MiB and "
            f"{free // 1024 ** 2} MiB are free. The machine was not stopped.")


def is_nfs(path):
    result = shell.subprocess_run(f'df -T {shlex.quote(path)}')
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
        if not safety.valid_backup_name(backup_name) or backup_name.startswith("files_"):
            raise ValueError('Invalid backup name.')
        disk_device = backup_name.split('_')[0]

        # Remove existing files inside restore folder
        shell.subprocess_run(f"rm -rf {shlex.quote(restore_path)}")

        # Create temporary folder to extract borg archive
        shell.subprocess_run(f"mkdir -p {shlex.quote(restore_path)}")

        # The disk is extracted here before it replaces the one of the machine: the machine is not stopped, and
        # nothing is written, when the disk of BackROLL could not hold it.
        file_browser.check_free_space(
            Path(restore_path), file_browser.archive_size(borg_repository, virtual_machine_info['name'], backup_name))

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
                    {shlex.quote(make_path(borg_repository, virtual_machine_info['name']))}::{shlex.quote(backup_name)}""")

            # Skip directories
            shell.os_system('mv $(find -type f) ./')

            # Loop through VM's disks to find filedisk
            for disk in vm_storage_info:
                if disk['device'] == disk_device:
                    break
            else:
                # Without this, the last disk of the machine would be replaced by a backup of another one.
                raise ValueError(
                    'Unable to match backup with existing diskfile. Aborting restore job')
            virtual_machine_disk = disk["source"]

            # Build path based on disk source path
            if "host" in virtual_machine_info:
                # For a KVM vm
                kvm_storagepath = make_path(
                    *list(filter(None, virtual_machine_disk.split("/")))[:-1], rooted=True, directory=True)
            else:
                # For a powered off CS vm. A machine of which the hypervisor did not answer is listed too:
                # its disk must not be replaced under a machine that runs.
                if str(virtual_machine_info.get('state', 'Stopped')).lower() != 'stopped':
                    raise ValueError(
                        f"The virtual machine is {virtual_machine_info.get('state')}: stop it before restoring a disk.")
                kvm_storagepath = make_path(
                    "/mnt", cs_manage_vm.listStorage(connector, disk)["id"], directory=True)

            if virtual_machine_disk == None:
                raise ValueError(
                    'Unable to match backup with existing diskfile. Aborting restore job')

            if "host" in virtual_machine_info:
                virtual_machine_diskName = virtual_machine_disk.split('/')[-1]
            else:
                virtual_machine_diskName = disk["path"]

            # The new disk is written next to the old one, which stays in place until the last step: without room
            # for it the machine is not even stopped.
            needed = extracted_size(virtual_machine_diskName)
            if needed:
                check_room_to_replace(kvm_storagepath, needed)

            # The way the machine is stopped and started depends on the machine, not on the pool: a pool linked to a
            # CloudStack connector can hold machines that CloudStack does not know (plain libvirt machines).
            managed_by_cloudstack = bool(connector_id) and bool(virtual_machine_info.get('cloudstack_instance'))

            def power_on():
                if "host" in virtual_machine_info:
                    if managed_by_cloudstack:
                        cs_vm_command.start_vm(
                            connector, virtual_machine_info['uuid'])
                    else:
                        kvm_manage_vm.start_vm(virtual_machine_info, hypervisor)

            stopped = False
            if "host" in virtual_machine_info:
                # Power off guest VM
                if managed_by_cloudstack:
                    cs_vm_command.stop_vm(
                        connector, virtual_machine_info['uuid'])
                else:
                    kvm_manage_vm.stop_vm(virtual_machine_info, hypervisor)
                stopped = True

            kvm_storage_disk_path = make_path(
                kvm_storagepath, virtual_machine_diskName)
            kvm_storage_disk_path_tmp = f"{kvm_storage_disk_path}.tmp"

            try:
                # subprocess.run(['cp', virtual_machine_diskName, kvm_storage_disk_path_tmp], check = True)
                shell.os_system(
                    f"cp {shlex.quote(virtual_machine_diskName)} {shlex.quote(kvm_storage_disk_path_tmp)}")

                # Fix permissions of new qcow2 filedisk
                # subprocess.run(['chmod', '644', kvm_storage_disk_path_tmp], check = True)
                shell.os_system(f"chmod 644 {shlex.quote(kvm_storage_disk_path_tmp)}")

                # Replace disk by extracted backup
                # subprocess.run(['mv', kvm_storage_disk_path_tmp, kvm_storage_disk_path], check = True)
                shell.os_system(
                    f"mv {shlex.quote(kvm_storage_disk_path_tmp)} {shlex.quote(kvm_storage_disk_path)}")

                # Remove temporary folder used to extract borg archive
                # subprocess.run(['rm', "-rf", restore_path])
                shell.os_system(f"rm -rf {shlex.quote(restore_path)}")
            except Exception as e:
                # The disk of the machine is still the old one (the copy is only moved in place at the end): the
                # partial copy is removed and the machine, that this restore stopped, is started again.
                try:
                    shell.os_system(f"rm -f {shlex.quote(kvm_storage_disk_path_tmp)}")
                except Exception as cleanup_error:
                    print(f"Unable to remove the partial copy. {cleanup_error}")
                if stopped:
                    try:
                        power_on()
                    except Exception as start_error:
                        print(f"Unable to start the machine again. {start_error}")
                raise e

            # Power on guest VM
            if stopped:
                power_on()

        except Exception as e:
            # Remove restore artifacts
            shell.subprocess_run(f"rm -rf {shlex.quote(restore_path)}")
            raise e
        print("Debug - restore_task - end")
    except Exception as e:

        # Remove restore artifacts
        try:
            shell.subprocess_run(f"rm -rf {shlex.quote(restore_path)}")
        except Exception as err:
            print(err)

        raise e
