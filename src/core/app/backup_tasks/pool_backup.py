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
from redis import Redis
from fastapi import Request
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

from sqlmodel import Session, select
import logging
import graypy

import random

import time

import logging

from app.routes import host
from app import database
from app.database import Hosts

from app.cloudstack import virtual_machine
from app.routes import host
from app.routes import storage
from app.borg import borg_core
from app.borg import borg_misc
from app.kvm import kvm_list_disk
from app.kvm import kvm_list_vm
from app.slack import messager
from app import task_handler

@celery.task(queue='backup_tasks', name='backup_subtask', soft_time_limit=5400)
def backup_subtask(info):

  def backup_sequence(info, host_info):
    # Initializing object
    backup_job = borg_core.borg_backup(info, host_info)
    try:
      # Retrieve VM info (name, id, disks, etc.)
      storage_repository = storage.retrieveStoragePathFromHostBackupPolicy(info)
      virtual_machine = info
      virtual_machine['storage'] = kvm_list_disk.getDisk(info, host_info)
      backup_job.init(virtual_machine, storage_repository)
    except:
      raise
    print(f"[ {info['name']} ] Pre-Flight checks incoming.")
    if backup_job.check_if_snapshot(info, host_info):
      print(f"[ {info['name']} ] VM is currently under snapshot. Checking disk files...")
      for disk in virtual_machine['storage']:
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
      for disk in virtual_machine['storage']:
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
      backup_job.create_snapshot()
    except Exception as e:
      raise e
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
        backup_job.borg_prune(disk)
      # Remove VM snapshot
      backup_job.delete_snapshot()
    except Exception as e:
      for disk in virtual_machine['storage']:
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
    redis_instance = Redis(host='redis', port=6379)
    unique_task_key = f'''nodup-single_vm_backup-{info}'''
    if not redis_instance.exists(unique_task_key):
      #I am the legitimate running task
      redis_instance.set(unique_task_key, "")
      redis_instance.expire(unique_task_key, 5400)
      try:
        # Retrieve VM host info
        host_info = jsonable_encoder(host.filter_host_by_id(info['host']))
        # Launch backup sequence
        backup_sequence(info, host_info)
      except:
        raise
    else:
      #Do you want to do something else on task duplicate?
      raise ValueError("This task is already running / scheduled")
    redis_instance.delete(unique_task_key)
  except Exception as e:
    redis_instance.delete(unique_task_key)
    # potentially log error with Sentry?
    # decrement the counter to insure tasks can run
    # or: raise e
    raise e

@celery.task(name='backup_completed', bind=True)
def backup_completed(target, *args, **kwargs):
  print('backup successfull !')

@celery.task(name='backup_failed', bind=True)
def backup_failed(target, *args, **kwargs):
  print('backup failed !')