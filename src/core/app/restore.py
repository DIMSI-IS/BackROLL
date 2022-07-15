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
from app.cloudstack import virtual_machine as cs_vm_command

borgserver_CS_repositorypath = os.getenv("CS_BACKUP_PATH")
borgserver_MGMT_repositorypath = os.getenv("MGMT_BACKUP_PATH")

regex = "^((?!^i-).)*$"

@celery.task(name='VM_Restore_Disk', bind=True, max_retries=3, base=QueueOnce)
def restore_disk_vm(self, virtual_machine_details, virtual_machine_id, backup_id):
  host_list = host.retrieve_host()
  virtual_machine_list = virtual_machine.parse_host(host_list)
  virtual_machine_info = virtual_machine.filter_virtual_machine_list(virtual_machine_list, virtual_machine_id)
  hypervisor = host.filter_host_by_id(virtual_machine_info['host'])
  try:
    restore_task(self, virtual_machine_info, hypervisor, virtual_machine_details, backup_id)
  except Exception:
    self.retry(countdown=3**self.request.retries)

# def restore_task(self, info, hypervisor, disk_list, backup):
def restore_task(self, virtual_machine_info, hypervisor, virtual_machine_details, backup_id):
  if re.search(regex, virtual_machine_info['name']):
    borg_repository = borgserver_MGMT_repositorypath
  else:
    borg_repository = borgserver_CS_repositorypath

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
            hostname=hypervisor['ip_address'],
            username=hypervisor['username']
      )

      # Extract selected borg archive
      os.system(f"""borg extract --sparse --strip-components=2 {borg_repository}{virtual_machine_info['name']}::{backup_id}""")

      # Loop through VM's disks to find filedisk
      for i in virtual_machine_details['disk_list']:
        if i['device'] == disk_device:
          break
      virtual_machine_disk = i['source']

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