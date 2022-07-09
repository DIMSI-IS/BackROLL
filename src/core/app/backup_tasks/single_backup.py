## Licensed to the Apache Software Foundation (ASF) under one
## or more contributor license agreements.  See the NOTICE file
## distributed with this work for additional information
## regarding copyright ownership.  The ASF licenses this file
## to you under the Apache License, Version 2.0 (the
## "License"); you may not use this file except in compliance
## with the License.  You may obtain a copy of the License at
##
##   http://www.apache.org/licenses/LICENSE-2.0
##
## Unless required by applicable law or agreed to in writing,
## software distributed under the License is distributed on an
## "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
## KIND, either express or implied.  See the License for the
## specific language governing permissions and limitations
## under the License.

#!/usr/bin/env python
from fastapi import Request
from fastapi.encoders import jsonable_encoder
from celery_once import QueueOnce
from celery import chord, chain, group, signature
from app import app

from app import celery
import traceback
import json
import re

import logging
import graypy

from app import database

from app.cloudstack import virtual_machine
from app.routes import host
from app.borg import borg_core
from app.borg import borg_misc
from app.kvm import kvm_list_disk
from app.kvm import kvm_list_vm
from app.slack import messager

def backup_deletion(self, info):
  # Initializing object
  delete_archive_job = borg_core.borg_backup(info, {})
  try:
    delete_archive_job.delete_archive(info)
  except ValueError as err:
    return {'status': 'error'}
    raise err
  delete_archive_job.close_connections()
  del delete_archive_job
  return {'status': 'success'}

def backup_creation(task, info):

  def backup_sequence(task, info, host_info):
    # Initializing object
    backup_job = borg_core.borg_backup(task, info, host_info)
    try:
      # Retrieve VM info (name, id, disks, etc.)
      backup_job.prepare(info, host_info)
      virtual_machine = kvm_list_disk.getDisk(info, host_info)
    except:
      raise
    print(f"[ {info['name']} ] Pre-Flight checks incoming.")
    if backup_job.check_if_snapshot(info, host_info):
      print(f"[ {info['name']} ] VM is currently under snapshot. Checking disk files...")
      for disk in virtual_machine['disk_list']:
        if ".snap" in disk['source']:
          print(f"[ {info['name']} ] Current {disk['device']} disk file is in '.snap' mode.")
          try:
            # Blockcommit changes to original disk file
            backup_job.blockcommit(disk)
            print(f"[ {info['name']} ] {disk['device']} disk file has been successfully blockcommitted.")
          except:
            backup_job.close_connections()
            del backup_job
            raise
        if backup_job.checking_files_trace(disk):
          print(f"[ {info['name']} ] Snap {disk['device']} disk file detected. Proceeding to deletion.")
          # Clean remaining snapshot files
          backup_job.remove_snapshot_file(disk)
          print(f"[ {info['name']} ] Snap {disk['device']} disk file has been deleted.")
      backup_job.delete_snapshot()
      print(f"[ {info['name']} ] Snapshot deleted.")
    else:
      for disk in virtual_machine['disk_list']:
        if backup_job.checking_files_trace(disk):
          print(f"[ {info['name']} ] Snap {disk['device']} disk file detected. Proceeding to deletion.")
          backup_job.remove_snapshot_file(disk)
          print(f"[ {info['name']} ] Snap {disk['device']} disk file has been deleted.")
    print(f"[ {info['name']} ] Virtual Machine is now in clean condition.")
    print(f"[ {info['name']} ] Pre-Flight checks done...")
    try:
      # Create full VM snapshot
      backup_job.create_snapshot(virtual_machine)
      # Check borg repository
      backup_job.check_repository()
      # Check borg repository lock status
      backup_job.check_repository_lock()
      # Loop through vm's disks
      for disk in virtual_machine['disk_list']:
        # Check if template (backing file) is backed up
        backup_job.manage_backing_file(disk)
        # Launch archive creation job
        backup_job.create_archive(disk)
        # Blockcommit changes to original disk file
        backup_job.blockcommit(disk)
        # Remove snapshot's remaining associated file
        backup_job.remove_snapshot_file(disk)
        # Borg Prune
        backup_job.borg_prune(disk)
      # Remove VM snapshot
      backup_job.delete_snapshot()
    except Exception as e:
      for disk in virtual_machine['disk_list']:
        try:
          # Blockcommit changes to original disk file
          backup_job.blockcommit(disk)
        except Exception as e:
          print(f"[ {info['name']} ] Unable to blockcommit {disk['device']} ({disk['source']}). Keep going...")
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
  try:
    # Retrieve VM host info
    host_info = jsonable_encoder(host.filter_host_by_id(info['host']))
    # Launch backup sequence
    backup_sequence(task, info, host_info)
  except Exception as e:
    raise e
  return { 'status': 'success' }

@celery.task(bind=True, queue='backup_tasks', name='Single_VM_Backup', base=QueueOnce)
def single_vm_backup(self, virtual_machine_info):

  if virtual_machine_info.get('state') == 'Running':
    try:
      backup_creation(self, virtual_machine_info)
    except Exception as err:
      raise err
  else:
    raise ValueError(f"Virtual machine with id {virtual_machine_info['uuid']} isn't running. Backup aborted.")

def delete_archive(info):
  remove_archive_task.delay(info)

@celery.task(name='Delete VM archive', bind=True, base=QueueOnce)
def remove_archive_task(self, info):
  try:
    backup_deletion(self, info)
  except ValueError as err:
    raise err


# Orphan backups cleaner (remove backup of non-existing VM)
@celery.task(name='backupCleaner')
def clean_orphan_backups():
  try:
    backup_list = borg_core.borg_list_backedup_vm()
  except ValueError as err:
    raise
  for i in backup_list:
    x = re.search("^(^i-).*", i)
    if x:
      parsedArchiveList.append(i)
  cleaning_repo_list = []
  cs_vm_list = virtual_machine.get_vm()
  for x in parsedArchiveList:
    vmexists = False
    for y in cs_vm_list['virtual_machine']:
      if x == y['instancename']:
        vmexists = True
    if not vmexists:
      cleaning_repo_list.append(x)

  vm_list_block = []

  for item in cleaning_repo_list:
    borg_core.delete_repository(item)
    vm_list_block.append({"type": "plain_text","text": item,"emoji": True })

  borg_core.close_connections()

  if len(vm_list_block) > 0:
    block_msg = {
      "blocks": [
        {
          "type": "section",
          "text": {
            "type": "mrkdwn",
            "text": "*I have detected that the following VMs*\n*no longer exists in Cloudstack but still have backups*"
          }
        },
        {
          "type": "divider"
        },
        {
          "type": "section",
          "fields": vm_list_block
        },
        {
          "type": "divider"
        },
        {
          "type": "section",
          "text": {
            "type": "mrkdwn",
            "text": "*These orphaned backups have been successfully cleaned up*"
          }
        }
      ]
    }
    messager.slack_notification(block_msg['blocks'])