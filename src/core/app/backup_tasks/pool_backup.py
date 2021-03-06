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
from celery_once import QueueOnce
from celery import chord, chain, group, signature
from celery.result import AsyncResult
from fastapi.encoders import jsonable_encoder
from app import app
from app import celery as celeryWorker
from app import celery
import traceback
import json
import re
import os

import logging
import graypy

import random

import time

import logging

from app.routes import host
from app import database

from app.cloudstack import virtual_machine
from app.routes import host
from app.borg import borg_core
from app.borg import borg_misc
from app.kvm import kvm_list_disk
from app.kvm import kvm_list_vm
from app.slack import messager
from app import task_handler

@celery.task(bind=True, queue='backup_tasks', name='backup_subtask', base=QueueOnce, time_limit=10800)
def backup_subtask(self, info):

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
            print(f"[ {info['name']} ] {disk['device']} disk file has been successfully blockcommitted.")
            # Close connections
            backup_job.close_connections()
            del backup_job
            raise
          if backup_job.checking_files_trace(disk):
            print(f"[ {info['name']} ] Snap {disk['device']} disk file detected. Proceeding to deletion.")
            # Clean remaining snapshot files
            try:
              backup_job.remove_snapshot_file(disk)
              print(f"[ {info['name']} ] Snap {disk['device']} disk file has been deleted.")
            except:
              raise
      backup_job.delete_snapshot()
      print(f"[ {info['name']} ] Snapshot deleted.")
    else:
      for disk in virtual_machine['disk_list']:
        if ".snap" in disk['source']:
          print(f"[ {info['name']} ] Current {disk['device']} disk file is in '.snap' mode.")
          try:
            # Blockcommit changes to original disk file
            backup_job.blockcommit(disk)
            print(f"[ {info['name']} ] {disk['device']} disk file has been successfully blockcommitted.")
          except:
            print(f"[ {info['name']} ] {disk['device']} disk file has been successfully blockcommitted.")
            del backup_job
            raise
          if backup_job.checking_files_trace(disk):
            print(f"[ {info['name']} ] Snap {disk['device']} disk file detected. Proceeding to deletion.")
            backup_job.remove_snapshot_file(disk)
            print(f"[ {info['name']} ] Snap {disk['device']} disk file has been deleted.")
    print(f"[ {info['name']} ] Virtual Machine is now in clean condition.")
    print(f"[ {info['name']} ] Pre-Flight checks done...")
    time.sleep(5)
    try:
      # Create full VM snapshot
      backup_job.create_snapshot(virtual_machine)
    except Exception as e:
      raise e
    try:
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
    backup_sequence(self, info, host_info)
  except:
    raise
  return { 'status': 'success' }


@celery.task(name='backup_completed', bind=True)
def backup_completed(target, *args, **kwargs):
  print('backup successfull !')

@celery.task(name='backup_failed', bind=True)
def backup_failed(target, *args, **kwargs):
  print('backup failed !')

@celery.task(name='Pool_VM_Backup', base=QueueOnce)
def pool_vm_backup(host_list):
  virtual_machine_list = []
  for host in host_list:
    HOST_UP  = True if os.system(f"nc -z -w 1 {host['ipaddress']} 22 > /dev/null") == 0 else False
    if HOST_UP and host['ssh'] == 1:
      try:
        virtual_machine_list.extend(kvm_list_vm.retrieve_virtualmachine(host))
      except Exception:
        raise        
  already_backuped_list = []

  for vm in virtual_machine_list:
    if vm['state'] == 'Running' and vm['id'] != -1 and vm not in already_backuped_list:
      already_backuped_list.append(vm)
      backup_subtask.delay(vm)