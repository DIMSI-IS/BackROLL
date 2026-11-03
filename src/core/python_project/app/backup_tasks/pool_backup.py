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
import time

from fastapi.encoders import jsonable_encoder

from app import backup_limit, policy_lookup
from app.backup_tasks import eligibility
from app.initialized import celery_app
from app.redis import new_redis_client

from app.routes import host
from app.routes import storage
from app.borg import borg_core
from app.kvm import kvm_list_disk
from app.virtual_machine_helper import check_disks_access

from app.routes import connectors
from app.routes import pool
from app.routes import backup_policy

from app.cloudstack import virtual_machine as cs_manage_vm


def run_backup_subtask(info):

    def backup_sequence(info, host_info=None):
        # Initializing object
        backup_job = borg_core.borg_backup(info, host_info)

        # Retrieve VM info (name, id, disks, etc.)
        storage_repository = storage.retrieveStoragePathFromHostBackupPolicy(
            info)
        virtual_machine = info
        if host_info:
            virtual_machine['storage'] = kvm_list_disk.getDisk(
                info, host_info)
        else:
            connector = connectors.filter_connector_by_id(
                pool.filter_pool_by_id(virtual_machine["pool_id"]).connector_id)
            virtual_machine['storage'] = cs_manage_vm.getDisk(
                connector, virtual_machine)

        backup_job.init(virtual_machine, storage_repository)

        check_disks_access(virtual_machine)

        if "host" in virtual_machine or virtual_machine.get('state') == 'Running':
            # Nothing is repaired here: a machine that is not as a backup needs it is refused (disk_safety).
            try:
                backup_job.preflight()
            except Exception:
                backup_job.close_connections()
                raise
        if "host" in virtual_machine or virtual_machine.get('state') == 'Running':
            try:
                # Create full VM snapshot
                backup_job.create_snapshot()
                # Check borg repository
                backup_job.check_repository()
                # Check borg repository lock status
                backup_job.check_repository_lock()
                # Folders and files of the policy, before the disks which are the main job
                backup_job.backup_files(policy_lookup.policy_of(virtual_machine))
                # Loop through vm's disks
                for disk in virtual_machine['storage']:
                    # Check if template (backing file) is backed up
                    backup_job.manage_backing_file(disk)
                    # Launch archive creation job
                    backup_job.create_archive(disk)
                    # Blockcommit changes to original disk file
                    backup_job.blockcommit(disk)
                    # Remove snapshot's remaining associated file
                    backup_job.remove_snapshot_file(disk)
                    # Borg Prune: each disk has its own archives
                    backup_job.borg_prune(disk, policy_lookup.policy_of(virtual_machine))
                # Remove VM snapshot
                backup_job.delete_snapshot()
                # Cleaning of the repository, if the storage asks for it (never fails the backup)
                backup_job.cleanup_after_backup()
                # Return backup name
                return backup_job.send_result()
            except Exception:
                # See single_backup: back on the disks when possible, no file deleted, the rest reported.
                try:
                    backup_job.recover()
                finally:
                    backup_job.close_connections()
                raise
        else:
            # Check borg repository
            backup_job.check_repository()
            # Check borg repository lock status
            backup_job.check_repository_lock()
            for disk in virtual_machine['storage']:
                # Launch archive creation job
                backup_job.create_archive(disk)

    redis_client = new_redis_client()
    try:
        # TODO Duplicated code ?
        vm_lock_key = backup_limit.acquire_vm_lock(redis_client, info)
        if vm_lock_key is not None:
            # The machine was not locked: it is now
            try:
                if 'host' in info:
                    # Retrieve VM host info
                    host_info = jsonable_encoder(
                        host.filter_host_by_id(info['host']))
                    # Launch backup sequence
                    backup_sequence(info, host_info)
                else:
                    backup_sequence(info)
            finally:
                redis_client.delete(vm_lock_key)
        else:
            # Duplicated key found in redis - target IS locked right now
            raise ValueError("This task is already running / scheduled")
    finally:
        redis_client.quit()

    return {'info': info, 'status': 'success'}


@celery_app.task(bind=True, queue='backup_tasks', name='backup_subtask', soft_time_limit=5400,
                 max_retries=None)
def backup_subtask(self, info):
    # See single_vm_backup: no waiting inside the time limit of a backup.
    skipped = eligibility.skipped(info)
    if skipped:
        return skipped
    member = backup_limit.try_acquire(str(info.get('name', info)))
    if member is None:
        raise self.retry(countdown=backup_limit.RETRY_SECONDS)
    try:
        return run_backup_subtask(info)
    finally:
        backup_limit.release(member)


@celery_app.task(name='backup_completed', bind=True)
def backup_completed(target, *args, **kwargs):
    print('backup successfull !')


@celery_app.task(name='backup_failed', bind=True)
def backup_failed(target, *args, **kwargs):
    print('backup failed !')
