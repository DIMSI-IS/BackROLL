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
from app.initialized import celery

import time
from app.routes import host
from app.routes import storage
from app.borg import borg_core
from app.kvm import kvm_list_disk
from app.virtual_machine_helper import check_disks_access

from app.routes import connectors
from app.routes import pool
from app.routes import backup_policy

from app.cloudstack import virtual_machine as cs_manage_vm


@celery.task(queue='backup_tasks', name='backup_subtask', soft_time_limit=5400)
def backup_subtask(info):

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
                            print(
                                f"[{info['name']}] {disk['device']} disk file has been successfully blockcommitted.")
                            # Close connections
                            backup_job.close_connections()
                            del backup_job
                            raise
                        if backup_job.checking_files_trace(disk):
                            print(
                                f"[{info['name']}] Snap {disk['device']} disk file detected. Proceeding to deletion.")
                            # Clean remaining snapshot files
                            try:
                                backup_job.remove_snapshot_file(disk)
                                print(
                                    f"[{info['name']}] Snap {disk['device']} disk file has been deleted.")
                            except:
                                raise
                backup_job.delete_snapshot()
                print(f"[{info['name']}] Snapshot deleted.")
            else:
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
                            print(
                                f"[{info['name']}] {disk['device']} disk file has been successfully blockcommitted.")
                            del backup_job
                            raise
                        if backup_job.checking_files_trace(disk):
                            print(
                                f"[{info['name']}] Snap {disk['device']} disk file detected. Proceeding to deletion.")
                            backup_job.remove_snapshot_file(disk)
                            print(
                                f"[{info['name']}] Snap {disk['device']} disk file has been deleted.")

            print(f"[{info['name']}] Virtual Machine is now in clean condition.")
        print(f"[{info['name']}] Pre-Flight checks done...")
        time.sleep(5)
        if "host" in virtual_machine or virtual_machine.get('state') == 'Running':
            try:
                # Create full VM snapshot
                backup_job.create_snapshot()
            except Exception as e:
                raise e
        if "host" in virtual_machine or virtual_machine.get('state') == 'Running':
            try:
                # Check borg repository
                backup_job.check_repository()
                # Check borg repository lock status
                backup_job.check_repository_lock()
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
                    # Borg Prune
                host_obj = host.filter_host_by_id(virtual_machine['host'])
                pool_obj = pool.filter_pool_by_id(host_obj.pool_id)
                backup_job.borg_prune(
                    disk, backup_policy.filter_policy_by_id(pool_obj.policy_id))
                # Remove VM snapshot
                backup_job.delete_snapshot()
                # Return backup name
                return backup_job.send_result()
            except Exception as e:
                for disk in virtual_machine['storage']:
                    try:
                        # Blockcommit changes to original disk file
                        backup_job.blockcommit(disk)
                    except Exception as e:
                        print(
                            f"[{info['name']}] Unable to blockcommit {disk['device']} ({disk['source']}). Keep going...")
                        print(e)
                    if backup_job.checking_files_trace(disk):
                        try:
                            # Clean remaining snapshot files
                            backup_job.remove_snapshot_file(disk)
                        except Exception as e:
                            # Close connections
                            backup_job.close_connections()
                            del backup_job
                            raise e
                # Close connections
                backup_job.close_connections()
                del backup_job
                raise e
        else:
            # Check borg repository
            backup_job.check_repository()
            # Check borg repository lock status
            backup_job.check_repository_lock()
            for disk in virtual_machine['storage']:
                # Launch archive creation job
                backup_job.create_archive(disk)

    redis_client = Redis(host='redis', port=6379)
    try:
        vm_lock_key = f'vmlock-{info}'
        if not redis_client.exists(vm_lock_key):
            # No duplicated key found in redis - target IS NOT locked right now
            redis_client.set(vm_lock_key, "")
            try:
                redis_client.expire(vm_lock_key, 5400)

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


@celery.task(name='backup_completed', bind=True)
def backup_completed(target, *args, **kwargs):
    print('backup successfull !')


@celery.task(name='backup_failed', bind=True)
def backup_failed(target, *args, **kwargs):
    print('backup failed !')
