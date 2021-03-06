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

import os
import re
import json
import subprocess
import os.path
from os import path
import calendar
import time
from datetime import date as getTodayDate
import paramiko
import libvirt
# Logging Module Imports
import logging
import graypy
# Libvirt dependencies Imports
import sys
from xml.dom import minidom
# KVM Connection Module Imports
from app.kvm import kvm_get_uuid
from app.kvm import kvm_list_disk
from app.kvm import kvm_list_snapshot

borgserver_CS_repositorypath = os.getenv("CS_BACKUP_PATH")
borgserver_MGMT_repositorypath = os.getenv("MGMT_BACKUP_PATH")


class borg_backup:
  """ Full sequence to backup all disks of a specified virtual machine
  Defining environment variables and logging file for backup task of specified VM"""

  def __init__(self, task, vm_info, host_info):
    self.env = dict(
        BORG_CS_REPO=borgserver_CS_repositorypath,
        BORG_KVM_REPO=borgserver_MGMT_repositorypath
    )
    self.task = task
    self.info = {}
    self.info['name'] = vm_info.get('name', None)
    self.info['borg_repository'] = None
    self.info['ip_address'] = host_info['ipaddress']
    self.info['username'] = host_info['username']
    self.virtual_machine = {}
    self.vm_name = ''

    if self.info['ip_address'] != None and self.info['username'] != None:
      # Starting hypervisor host ssh access
      self.host_ssh = paramiko.SSHClient()
      self.host_ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
      self.host_ssh.connect(
          hostname=self.info['ip_address'],
          username=self.info['username']
    )

  def remote_request(self, command):
    # Passing commands through SSH to remote endpoint
    try:
      stdin, stdout, stderr = self.host_ssh.exec_command(command)
    except:
      raise ValueError('Unable to connect to KVM host !')
    rc = stdout.channel.recv_exit_status()
    stderr = stderr.readlines()
    stdout = stdout.readlines()
    return {'rc': rc, 'stdout': stdout, 'stderr': stderr}

  def close_connections(self):
    # closing hypervisor and borg ssh access
    try:
      self.host_ssh.close()
    except:
      pass
    try:
      self.borgSSH.close()
    except:
      pass
  def process_rc(self, request, shell, remote=False):
    """ Processing return code of specified command """
    # Locally runned command
    if not remote:
      if shell == 'bash':
        if request.returncode == 1:
          print(request.stderr.decode("utf-8"))
          raise ValueError(request.stderr.decode("utf-8"))
      elif shell == 'borg' and request.returncode == 2:
        print(request.stderr.decode("utf-8"))
        raise ValueError(request.stderr.decode("utf-8"))
    # Remotely runned command
    else:
      if shell == 'bash':
        if request['rc'] == 1:
          error_message = (request['stderr'][0:1] or ('',))[0]
          print(error_message)
          raise ValueError(error_message)
        else:
          return request['stdout']
      elif shell == 'borg':
        if request['rc'] == 2:
          error_message = (request['stderr'][0:1] or ('',))[0]
          print(error_message)
          raise ValueError(error_message)
        else:
          return request['stdout']
      if len(request['stdout']) > 0:
        print(request['stdout'][0])
        return request['stdout']
      elif request['stdout'] != []:
        print(request['stdout'])
        return request['stdout']

  def prepare(self, vm_info, host_info):
    self.vm_name = self.info['name']
    print(f'[ {self.vm_name} ] Gathering data...')
    if re.search("^((?!^i-).)*$", self.info['name']):
      print(f'[ {self.vm_name} ] VM is detected as part of Management. Using MGMT BORG repository')
      self.info['borg_repository'] = self.env['BORG_KVM_REPO']
    else:
      print(f'[ {self.vm_name} ] VM is detected as part of CloudStack. Using CS BORG repository')
      self.info['borg_repository'] = self.env['BORG_CS_REPO']
    self.virtual_machine = kvm_list_disk.getDisk(vm_info, host_info)
    disk_number = len(self.virtual_machine['disk_list'])
    print(f'[ {self.vm_name} ] Disk(s) found : {disk_number}')

  def check_repository(self):
    self.vm_name = self.info['name']
    repository = self.info['borg_repository']
    # Check if borg repository folder exists
    if os.path.exists(f"{repository}{self.vm_name}"):
      # Borg repo exists
      print(f'[ {self.vm_name} ] A Borg repository for this VM has been found')
    else:
      # Borg repo doesn't exist
      print(f'[ {self.vm_name} ] Borg repository for this VM doesn\'t exist. Creating a new one')
      subprocess.run(["mkdir", "-p", f"{repository}/{self.vm_name}"], check=True)
      # Initializing borg repository
      print(f'[ {self.vm_name} ] Initializing the new borg repo')
      subprocess.run(["borg", "init", "--encryption", "none", f"{repository}{self.vm_name}"], check=True)
    print(f'[ {self.vm_name} ] Borg repository setup is OK')

  def check_repository_lock(self):
    self.vm_name = self.info['name']
    print(f'[ {self.vm_name} ] Checking borg repository lock status')
    # Check if borg repo is locked
    repository = self.info['borg_repository']
    request = subprocess.run(["borg", "list", f"{repository}{self.vm_name}"], capture_output=True)
    if request.returncode == 0:
      print(f'[ {self.vm_name} ] Borg repository is unlocked, job will continue')
    else:
      print(f'[ {self.vm_name} ] Borg repository is locked, job will stop')
      raise ValueError(request.stderr.decode("utf-8"))

  def checking_files_trace(self, disk):
    if os.path.exists(f'{disk["source"].replace(".snap", "")}.snap'):
      return True
    else:
      return False

  def check_if_snapshot(self, info, host_info):
    vm_state = kvm_list_snapshot.get_snapshot(info, host_info)
    if vm_state['snapshot'] == 1:
      print(f"[ {self.virtual_machine['name'] }] A snapshot has been detected !")
      return True
    else:
      print(f"[ {self.virtual_machine['name'] }] No snapshot detected")
      return False

  def create_snapshot(self, virtual_machine):
    vm_name = self.virtual_machine['name']
    print(f'[ {vm_name} ] Snapshotting virtual machines disks')
    command = f'LIBVIRT_DEFAULT_URI=qemu:///system virsh snapshot-create-as \
        --domain {vm_name} {vm_name}.snap \
        --quiesce \
        --atomic \
        --disk-only'
    for disk in virtual_machine['disk_list']:
      new_disk = disk['source'].replace(".snap", "")
      command += f" --diskspec {disk['device']},file={new_disk}.snap,snapshot=external"
    request = self.remote_request(command)
    self.process_rc(request, 'bash', remote=True)

  def manage_backing_file(self, disk):
    repository = self.info['borg_repository']
    vm_name = self.virtual_machine['name']
    request = subprocess.run(["qemu-img", "info", "--output=json", disk['source']], capture_output=True)
    qemu_img_info = request.stdout.decode("utf-8")
    qemu_img_info = json.loads(qemu_img_info)
    if qemu_img_info.get('full-backing-filename'):
      print(f'[{vm_name}] Checking that {vm_name}\'s backing file has already been backed up')
      backing_file = qemu_img_info['full-backing-filename'].split('/')[-1]
      if not path.isfile(f"{repository}template/{backing_file}"):
        print(f'[{vm_name}] Backing up the backing file...')
        os.system(f"""cp {qemu_img_info['full-backing-filename']} {repository}template/{backing_file}""")
        print(f'[{vm_name}] Backing up the backing file has successfully completed')

  def create_archive(self, disk):
    repository = self.info['borg_repository']
    vm_name = self.virtual_machine['name']
    disk_source = ((disk['source']).split('.'))[0]
    disk_name = disk['device']

    print(f'[{vm_name}] Creating borg archive for disk {disk_name}')

    cmd = f'borg create \
        --log-json \
        --progress \
        {repository}{vm_name}::{disk_name}_{disk_source.split("/")[-1]}_{calendar.timegm(time.gmtime())} \
        {disk_source}'

    operation = None

    process = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    while True:
      process.stdout.flush()
      output = process.stdout.readline()
      if output == '' and process.poll() is not None:
        break
      elif not output and process.poll() is not None:
        break
      if output:
        parsed_output = json.loads(output.strip().decode("utf-8"))
        meta = {'done': None, 'total': None, 'percentage': None}
        parsed_output = json.loads(output.strip().decode("utf-8"))

        current_operation  = parsed_output.get('operation', None)
        current = parsed_output.get('current', None)
        total = parsed_output.get('total', None)
        progressionPercentage = None

        if current and total:
          progressionPercentage = (int(parsed_output['current']) / int(parsed_output['total'])) * 100

        if current_operation:
          operation = current_operation
          self.task.update_state(state='PROGRESS', meta={'current': current, 'total': total, 'percentage': progressionPercentage, 'step': f'{current_operation}/4'})
        else:
          self.task.update_state(state='PROGRESS', meta={'current': current, 'total': total, 'percentage': progressionPercentage, 'step': f'{operation}/4'})

    print(f'[{vm_name}] Borg archive successfully created for {disk_name}')

  def blockcommit(self, disk):
    vm_name = self.virtual_machine['name']
    disk_name = disk['device']
    command = f'LIBVIRT_DEFAULT_URI=qemu:///system virsh blockcommit {vm_name} {disk_name} \
        --base {disk["source"].replace(".snap", "")} \
        --top {disk["source"].replace(".snap", "")}.snap \
        --active \
        --verbose \
        --pivot'
    request = self.remote_request(command)
    self.process_rc(request, 'bash', remote=True)
    print(f"[{vm_name}] Disk {disk_name} has been successfully blockcommited to {disk['source']}")

  def delete_snapshot(self):
    vm_name = self.virtual_machine['name']
    command = f'LIBVIRT_DEFAULT_URI=qemu:///system virsh snapshot-delete {vm_name} --metadata {vm_name}.snap'
    request = self.remote_request(command)
    self.process_rc(request, 'bash', remote=True)
    print(f'[{vm_name}] Snapshot {vm_name}.snap has been successfully deleted')

  def remove_snapshot_file(self, disk):
    vm_name = self.virtual_machine['name']
    disk_name = disk['device']
    disk_source = f"""{disk['source'].split('.')[0]}.snap"""
    os.remove(disk_source)
    print(f"[ {vm_name} ] Successfully removed snapshot file '{disk_source}' for disk {disk_name}")

  def borg_prune(self, disk):
    disk_name = disk['device']
    repository = self.info['borg_repository']
    command = f'borg prune --keep-daily 30 --prefix "{disk_name}" {repository}{self.vm_name}'
    subprocess.run(command.split(),check=True)

  def clean_failed_job(self, vm_info, host_info):
    print(f"[ {self.virtual_machine['name'] }] Reverting changes due to backup job failure...")
    parsevm_info = kvm_list_snapshot.get_snapshot(vm_info, host_info)

    if parsevm_info['snapshot'] == 1:

      print(f"[ {self.virtual_machine['name']} ] A snapshot has been detected")
      for disk in self.virtual_machine['disk_list']:
        try:
          self.blockcommit(disk)
        except Exception:
          pass
        self.delete_snapshot()
    else:
      print(f"[ {self.virtual_machine['name']} ] No snapshot detected")
      for disk in self.virtual_machine['disk_list']:
        if checking_files_trace(disk) == True:
          print(f"[ {self.virtual_machine['name']} ] Deleting old snapshot file")
          self.remove_snapshot_file(disk)
    print(f"[ {self.virtual_machine['name']} ] End of cleaning job. We can now relaunch backup task for this VM")

    for disk in self.virtual_machine['disk_list']:
      if ".snap" in disk['source']:
        print(f"[ {self.virtual_machine['name']} ] Warning: Disk file in use is a snapshot file !")
        print(f"[ {self.virtual_machine['name']} ] Trying to blockcommit snapshot file to {disk['source']}...")
        try:
          self.blockcommit(disk)
          print(f"[ {self.virtual_machine['name']} ] Successfully blockcommited {disk['device']}")
          try:
            self.remove_snapshot_file(disk)
            print(f"[ {self.virtual_machine['name']} ] Snapshot file has been deleted")
          except Exception:
            raise ValueError(f"[ {self.virtual_machine['name']} ] Unable to remove snapshot file. Manual action required")
        except Exception:
          print(f"[ {self.virtual_machine['name']} ] Unable to blockcommit file {disk['source']} for disk {disk['device']}. Manual action may be required")

  def delete_archive(self, payload):
    repository = self.info['borg_repository']
    command = f'borg delete {repository}{payload["target"]["name"]}::{payload["selected_backup"]["name"]}'
    request = self.remote_request(command)
    self.process_rc(request, 'borg')

def borg_list_backup(virtual_machine):
  try:
    # Starting ssh access
    if re.search("^((?!^i-).)*$", virtual_machine):
      command = f"borg list --json {borgserver_MGMT_repositorypath}{virtual_machine}"
    else:
      command = f"borg list --json {borgserver_CS_repositorypath}{virtual_machine}"
    request = subprocess.run(command.split(), capture_output=True)
    result = ""
    if request.returncode == 2:
      if 'lock' in request.stderr.decode("utf-8"):
        result = '{"archives": [], "state": "locked"}'
      else:
        result = '{"archives": [], "state": "unlocked"}'
    else:
      result = request.stdout.decode("utf-8")
    return result
  except ValueError as err:
    print(err.args[0])
    raise


def borg_list_backedup_vm():
  try:
    result = os.listdir(borgserver_CS_repositorypath)
    return result
  except Exception as e:
    print(e)
    raise e

def delete_repository(self, repository):
  command = f'borg delete {borgserver_CS_repositorypath}{repository}'
  print(command)
  stdin, stdout, stderr = self.borgSSH.exec_command(command)
  stdin.write('YES' + '\n')
  if stdout.channel.recv_exit_status() == 2:
    for line in iter(stderr.readline, ""):
      reason = ''
      reason += line
    print(reason)
  else:
    for line in iter(stdout.readline, ""):
      output += line
    print(output)
