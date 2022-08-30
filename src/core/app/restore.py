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
import os
import logging
import subprocess
from datetime import datetime
from fastapi import Request
from celery_once import QueueOnce
from app import app
from app import celery as celeryWorker
from app import celery
import traceback
import json
import paramiko
import re

from app import task_handler
from app.routes import virtual_machine
from app.routes import host
from app.routes import storage
from app.cloudstack import virtual_machine as cs_vm_command

regex = "^((?!^i-).)*$"

@celery.task(name='VM_Restore_Disk', bind=True, max_retries=3, base=QueueOnce)
def restore_disk_vm(self, info, backup_id):
  try:
    redis_instance = Redis(host='redis', port=6379)
    unique_task_key = f'''vmlock-{virtual_machine_info}'''
    if not redis_instance.exists(unique_task_key):
      #I am the legitimate running task
      redis_instance.set(unique_task_key, "")
      redis_instance.expire(unique_task_key, 5400)
      try:
        # Retrieve VM host info
        host_info = jsonable_encoder(host.filter_host_by_id(info['host']))
        vm_storage_info = kvm_list_disk.getDisk(info, host_info)
        try:
          restore_task(self, info, host_info, vm_storage_info, backup_id)
        except Exception:
          self.retry(countdown=3**self.request.retries)
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

# def restore_task(self, info, hypervisor, disk_list, backup):
def restore_task(self, virtual_machine_info, hypervisor, vm_storage_info, backup_id):

  vm_storage = storage.retrieveStoragePathFromHostBackupPolicy(virtual_machine_info)
  borg_repository = vm_storage.path

  def remote_request(host_ssh, command):
    # Passing commands through SSH to remote endpoint
    try:
      stdin, stdout, stderr = host_ssh.exec_command(command)
    except:
      raise ValueError('Unable to connect to KVM host !')
    rc = stdout.channel.recv_exit_status()
    stderr = stderr.readlines()
    stdout = stdout.readlines()
    return {'rc': rc, 'stdout': stdout, 'stderr': stderr}

  def process_rc(request, shell):
    """ Processing return code of specified command """
    if shell == 'bash':
      if request.returncode == 1:
        logging.error(request.stderr.decode("utf-8"))
        raise ValueError(request.stderr.decode("utf-8"))
    elif shell == 'borg':
      if request.returncode == 2:
        logging.error(request.stderr.decode("utf-8"))
        raise ValueError(request.stderr.decode("utf-8"))

  try:

    disk_device = backup_id.split('_')[0]

    # Remove existing files inside restore folder
    command = f"rm -rf {borg_repository}restore/{virtual_machine_info['name']}"
    request = subprocess.run(command.split())  

    # Create temporary folder to extract borg archive
    command = f"mkdir -p {borg_repository}restore/{virtual_machine_info['name']}"
    request = subprocess.run(command.split())

    # Go into directory
    os.chdir(f"{borg_repository}restore/{virtual_machine_info['name']}")

    try:
      if re.search(regex, virtual_machine_info['name']):
        host_ssh = paramiko.SSHClient()
        host_ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        host_ssh.connect(
            hostname=hypervisor['ipaddress'],
            username=hypervisor['username']
      )

      # Extract selected borg archive
      os.system(f"""borg extract --sparse --strip-components=2 {borg_repository}{virtual_machine_info['name']}::{backup_id}""")

      # Loop through VM's disks to find filedisk
      print(vm_storage_info)
      for disk in vm_storage_info['storage']:
        if disk['device'] == disk_device:
          break
      virtual_machine_disk = disk['source']

      # Build path based on disk source path
      path = virtual_machine_disk.split("/")
      del path[-1]
      del path[0]
      kvm_storagepath = ""
      for item in path:
        kvm_storagepath += f"/{item}"
      kvm_storagepath += "/"
      

      if virtual_machine_disk == None:
        raise ValueError('Unable to match backup with existing diskfile. Aborting restore job')
      virtual_machine_diskName = virtual_machine_disk.split('/')[-1]

      # Power off guest VM
      if re.search(regex, virtual_machine_info['name']):
        command = f"LIBVIRT_DEFAULT_URI=qemu:///system virsh destroy {virtual_machine_info['name']}"
        remote_request(host_ssh, command)
      else:
        cs_vm_command.stop_vm(virtual_machine_info['uuid'])

      # Replace existing diskfile with restored file
      os.system(f"cp {virtual_machine_diskName} {kvm_storagepath}{virtual_machine_diskName}-tmp")

      # Fix chmod ownership of new qcow2 filedisk
      os.system(f"chmod 644 {kvm_storagepath}{virtual_machine_diskName}-tmp")

      # Replace disk by extracted backup
      os.system(f"mv {kvm_storagepath}{virtual_machine_diskName}-tmp {kvm_storagepath}{virtual_machine_diskName}")

      # Remove temporary folder used to extract borg archive
      os.system(f"rm -rf {borg_repository}restore/{virtual_machine_info['name']}")

      if re.search(regex, virtual_machine_info['name']):
        command = f"LIBVIRT_DEFAULT_URI=qemu:///system virsh start {virtual_machine_info['name']}"
        remote_request(host_ssh, command)
        host_ssh.close()
      else:
        # Power on guest VM
        cs_vm_command.start_vm(virtual_machine_info['uuid'])

    except Exception as e:
      # Remove restore artifacts
      command = f"rm -rf {borg_repository}restore/{virtual_machine_info['name']}"
      request = subprocess.run(command.split())
      raise e

  except Exception as e:

    # Remove restore artifacts
    try:
      command = f"rm -rf {borg_repository}restore/{virtual_machine_info['name']}"
      request = subprocess.run(command.split())
    except Exception as err:
      print(err)

    raise e