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
from redis import Redis
from fastapi.encoders import jsonable_encoder
from celery_once import QueueOnce
from app import celery
from app.routes import host
from app.routes import storage
from app.borg import borg_core
from app.kvm import kvm_list_disk

from app.routes import connectors
from app.routes import pool
from app.routes import backup_policy

from app.cloudstack import virtual_machine as cs_manage_vm


def backup_creation(info):

    def backup_sequence(info, host_info=None):
        # Initializing object
        backup_job = borg_core.borg_backup(info, host_info)
        try:
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
        except:
            raise
        if "host" in virtual_machine or virtual_machine.get('state') == 'Running':
            print(f"[{info['name']}] Pre-Flight checks incoming.")
            if backup_job.check_if_snapshot():
                print(
                    f"[{info['name']}] VM is currently under snapshot. Checking disk files...")
                for disk in virtual_machine['storage']:
                    if ".snap" in disk['source']:
                        print(
                            f"[{info['name']}] Current {disk['device']} disk file is in '.snap' mode.")
                        try:
                            # Blockcommit changes to original disk file
                            backup_job.blockcommit(disk)
                            print(
                                f"[{info['name']}] {disk['device']} disk file has been successfully blockcommitted.")
                        except:
                            backup_job.close_connections()
                            del backup_job
                            raise
                    if backup_job.checking_files_trace(disk):
                        print(
                            f"[{info['name']}] Snap {disk['device']} disk file detected. Proceeding to deletion.")
                        # Clean remaining snapshot files
                        backup_job.remove_snapshot_file(disk)
                        print(
                            f"[{info['name']}] Snap {disk['device']} disk file has been deleted.")
                backup_job.delete_snapshot()
                print(f"[{info['name']}] Snapshot deleted.")
            else:
                for disk in virtual_machine['storage']:
                    if backup_job.checking_files_trace(disk):
                        print(
                            f"[{info['name']}] Snap {disk['device']} disk file detected. Proceeding to deletion.")
                        backup_job.remove_snapshot_file(disk)
                        print(
                            f"[{info['name']}] Snap {disk['device']} disk file has been deleted.")
            print(f"[{info['name']}] Virtual Machine is now in clean condition.")
            print(f"[{info['name']}] Pre-Flight checks done...")
        try:
            # If virtual machine is KVM only
            if "host" in virtual_machine or virtual_machine.get('state') == 'Running':
                # Create full VM snapshot
                backup_job.create_snapshot()
            # Check borg repository
            backup_job.check_repository()
            # Check borg repository lock status
            backup_job.check_repository_lock()
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
                host_obj = host.filter_host_by_id(virtual_machine['host'])
                pool_obj = pool.filter_pool_by_id(host_obj.pool_id)
                backup_job.borg_prune(
                    disk, backup_policy.filter_policy_by_id(pool_obj.policy_id))
            if "host" in virtual_machine or virtual_machine.get('state') == 'Running':
                # Remove VM snapshot
                backup_job.delete_snapshot()
            # Return backup name
            return backup_job.send_result()
        except Exception as backup_error:
            for disk in virtual_machine['storage']:
                try:
                    # Blockcommit changes to original disk file
                    backup_job.blockcommit(disk)
                except Exception as bcommit_error:
                    print(
                        f"[{info['name']}] Unable to blockcommit {disk['device']} ({disk['source']}). Keep going...")
                    print(bcommit_error)
                if backup_job.checking_files_trace(disk):
                    try:
                        # Clean remaining snapshot files
                        backup_job.remove_snapshot_file(disk)
                    except Exception as cleaning_error:
                        # Close connections
                        backup_job.close_connections()
                        del backup_job
                        raise cleaning_error
            # Close connections
            backup_job.close_connections()
            del backup_job
            raise backup_error
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


@celery.task(queue='backup_tasks', name='Single_VM_Backup', soft_time_limit=5400)
def single_vm_backup(virtual_machine_info):
    redis_client = Redis(host='redis', port=6379)
    try:
        vm_lock_key = f'vmlock-{virtual_machine_info}'
        if not redis_client.exists(vm_lock_key):
            # No duplicated key found in redis - target IS NOT locked right now
            redis_client.set(vm_lock_key, "")
            try:
                redis_client.expire(vm_lock_key, 5400)

                return backup_creation(virtual_machine_info)
            finally:
                redis_client.delete(vm_lock_key)
        else:
            # Duplicated key found in redis - target IS locked right now
            raise ValueError("This task is already running / scheduled")
    finally:
        redis_client.quit()


# # Orphan backups cleaner (remove virtual machine borg's repository (and all of it's data) of any non-existing VM)
# @celery.task(name='garbageCollector')
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
