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


def backup_creation(info):

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
        try:
            # If virtual machine is KVM only
            if "host" in virtual_machine or virtual_machine.get('state') == 'Running':
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
                if "host" in virtual_machine or virtual_machine.get('state') == 'Running':
                    # Check if template (backing file) is backed up
                    backup_job.manage_backing_file(disk)
                # Launch archive creation job
                backup_job.create_archive(disk)
                if "host" in virtual_machine or virtual_machine.get('state') == 'Running':
                    # Blockcommit changes to original disk file
                    backup_job.blockcommit(disk)
                # Borg Prune
                backup_job.borg_prune(disk, policy_lookup.policy_of(virtual_machine))
            if "host" in virtual_machine or virtual_machine.get('state') == 'Running':
                # Remove VM snapshot
                backup_job.delete_snapshot()
            # Cleaning of the repository, if the storage asks for it (never fails the backup)
            backup_job.cleanup_after_backup()
            # Return backup name
            return backup_job.send_result()
        except Exception as backup_error:
            # The machine goes back on its disks when it can. No file is deleted here: what can not be brought
            # back is reported (NEEDS_ATTENTION) and left for an administrator.
            try:
                backup_job.recover()
            finally:
                backup_job.close_connections()
            raise
    try:
        # Retrieve VM host info
        # print px
        if 'host' in info:
            host_info = jsonable_encoder(host.filter_host_by_id(info['host']))
            # Launch backup sequence
            return backup_sequence(info, host_info)
        else:
            return backup_sequence(info)
    except Exception as sequence_error:
        raise sequence_error


def run_single_vm_backup(virtual_machine_info):
    redis_client = new_redis_client()
    try:
        # TODO Duplicated code ?
        vm_lock_key = backup_limit.acquire_vm_lock(redis_client, virtual_machine_info)
        if vm_lock_key is not None:
            # The machine was not locked: it is now
            try:
                return backup_creation(virtual_machine_info)
            finally:
                redis_client.delete(vm_lock_key)
        else:
            # Duplicated key found in redis - target IS locked right now
            raise ValueError("This task is already running / scheduled")
    finally:
        redis_client.quit()


@celery_app.task(bind=True, queue='backup_tasks', name='Single_VM_Backup', soft_time_limit=5400,
                 max_retries=None)
def single_vm_backup(self, virtual_machine_info):
    # The number of backups at the same time is a setting. A backup that finds no free place goes back
    # to the queue: it must not wait here, inside the 90 minutes that a backup is allowed to take.
    # max_retries=None on the task: given to retry() it would mean "the default of the task" (3 retries,
    # 45 seconds), and a backup that waits for its turn would fail.
    skipped = eligibility.skipped(virtual_machine_info)
    if skipped:
        return skipped
    member = backup_limit.try_acquire(str(virtual_machine_info))
    if member is None:
        raise self.retry(countdown=backup_limit.RETRY_SECONDS)
    try:
        return run_single_vm_backup(virtual_machine_info)
    finally:
        backup_limit.release(member)


# # Orphan backups cleaner (remove virtual machine borg's repository (and all of it's data) of any non-existing VM)
# @celery_app.task(name='garbageCollector')
# def garbage_collector():
#   parsedArchiveList = []
#   try:
#     backup_list = borg_core.borg_list_backedup_vm()
#   except ValueError as err:
#     raise
#   for i in backup_list:
#     x = re.search("^(^i-).*", i)
#     if x:
#       parsedArchiveList.append(i)
#   cleaning_repo_list = []
#   cs_vm_list = virtual_machine.get_vm()
#   for x in parsedArchiveList:
#     vmexists = False
#     for y in cs_vm_list['virtual_machine']:
#       if x == y['instancename']:
#         vmexists = True
#     if not vmexists:
#       cleaning_repo_list.append(x)

#   vm_list_block = []

#   for item in cleaning_repo_list:
#     borg_core.delete_repository(item)
#     vm_list_block.append({"type": "plain_text","text": item,"emoji": True })

#   borg_core.close_connections()

#   if len(vm_list_block) > 0:
#     block_msg = {
#       "blocks": [
#         {
#           "type": "section",
#           "text": {
#             "type": "mrkdwn",
#             "text": "*I have detected that the following VMs*\n*no longer exists in Cloudstack but still have backups*"
#           }
#         },
#         {
#           "type": "divider"
#         },
#         {
#           "type": "section",
#           "fields": vm_list_block
#         },
#         {
#           "type": "divider"
#         },
#         {
#           "type": "section",
#           "text": {
#             "type": "mrkdwn",
#             "text": "*These orphaned backups have been successfully cleaned up*"
#           }
#         }
#       ]
#     }
#     slack.connector(block_msg['blocks'])
