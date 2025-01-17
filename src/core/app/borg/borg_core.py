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

import os
import json
import subprocess
import os.path
from os import path
from pathlib import Path
import calendar
import time
import paramiko
import shutil

from app.routes import pool
from app.routes import connectors

# KVM custom module import
from app.kvm import kvm_manage_snapshot

# CS custom module import
from app.cloudstack import virtual_machine as cs_manage_vm

from app.patch import make_path


class borg_backup:
    """ Full sequence to backup all disks of a specified virtual machine
    Defining environment variables and logging file for backup task of specified VM"""

    def __init__(self, vm_info, host_info):
        self.info = {}
        self.info['name'] = vm_info.get('name', None)
        self.info['borg_repository'] = None
        if host_info:
            self.info['ip_address'] = host_info['ipaddress']
        if host_info:
            self.info['username'] = host_info['username']
        self.info['vm_info'] = vm_info
        if host_info:
            self.info['host_info'] = host_info
        self.info['backup_name'] = None
        self.virtual_machine = {}
        self.vm_name = ''

        if 'ip_address' in self.info and 'username' in self.info:
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

    def process_rc(self, request):
        """ Processing return code of specified command """
        # Locally runned command
        if request.returncode == 2:
            print(request.stderr.decode("utf-8"))
            raise ValueError(request.stderr.decode("utf-8"))

    def init(self, virtual_machine, storage):
        self.vm_name = self.info['name']
        print(f'[{self.vm_name}] Gathering data...')
        self.info['borg_repository'] = storage['path']
        self.virtual_machine = virtual_machine
        disk_number = len(self.virtual_machine['storage'])
        print(f'[{self.vm_name}] Disk(s) found : {disk_number}')

    def check_repository(self):
        self.vm_name = self.info['name']
        vm_repository_path = make_path(
            self.info['borg_repository'], self.vm_name)
        # Check if borg repository folder exists
        if os.path.exists(vm_repository_path):
            # Borg repo exists
            print(f'[{self.vm_name}] A Borg repository for this VM has been found')
        else:
            # Borg repo doesn't exist
            print(
                f'[{self.vm_name}] Borg repository for this VM doesn\'t exist. Creating a new one')
            Path(vm_repository_path).mkdir(parents=True, exist_ok=True)
            # Initializing borg repository
            print(f'[{self.vm_name}] Initializing the new borg repo')
            subprocess.run(["borg", "init", "--encryption",
                           "none", vm_repository_path], check=True)
        print(f'[{self.vm_name}] Borg repository setup is OK')

    def check_repository_lock(self):
        self.vm_name = self.info['name']
        print(f'[{self.vm_name}] Checking borg repository lock status')
        # Check if borg repo is locked
        vm_repository_path = make_path(
            self.info['borg_repository'], self.vm_name)
        request = subprocess.run(
            ["borg", "list", vm_repository_path], capture_output=True)
        if request.returncode == 0:
            print(f'[{self.vm_name}] Borg repository is unlocked, job will continue')
        else:
            print(f'[{self.vm_name}] Borg repository is locked, job will stop')
            raise ValueError(request.stderr.decode("utf-8"))

    def checking_files_trace(self, disk):
        # TODO replace .snap by .snap ?
        if os.path.exists(f'{disk["source"].replace(".snap", "")}.snap'):
            return True
        else:
            return False

    def check_if_snapshot(self):
        vm_state = kvm_manage_snapshot.get_snapshot(
            self.info['vm_info'], self.info['host_info'])
        if vm_state['snapshot'] == 1:
            print(
                f"[{self.virtual_machine['name'] }] A snapshot has been detected !")
            return True
        else:
            print(f"[{self.virtual_machine['name'] }] No snapshot detected")
            return False

    def create_snapshot(self):
        vm_name = self.virtual_machine['name']
        print(f'[{vm_name}] Snapshotting virtual machines disks')
        snapshot_xml = kvm_manage_snapshot.generate_xmlSnapshot(
            vm_name, self.virtual_machine['storage'])
        kvm_manage_snapshot.createSnapshot(
            self.info['vm_info'], self.info['host_info'], snapshot_xml)

    def manage_backing_file(self, disk):
        repository = self.info['borg_repository']
        vm_name = self.virtual_machine['name']
        print(f"[{vm_name}] Getting information about disk at {disk['source']}")
        request = subprocess.run(
            ["qemu-img", "info", "--output=json", disk['source']], capture_output=True)
        qemu_img_info = request.stdout.decode("utf-8")
        qemu_img_info = json.loads(qemu_img_info)
        if qemu_img_info.get('full-backing-filename'):
            print(
                f'[{vm_name}] Checking that {vm_name}\'s backing file has already been backed up')
            backing_file = qemu_img_info['full-backing-filename'].split(
                '/')[-1]
            template_path = make_path(repository, "template", backing_file)

            if not path.exists(template_path):
                os.makedirs(template_path)

            if not path.isfile(template_path):
                print(f'[{vm_name}] Backing up the backing file...')
                shutil.copy(
                    qemu_img_info['full-backing-filename'], template_path)
                print(
                    f'[{vm_name}] Backing up the backing file has successfully completed')

    def create_archive(self, disk):
        repository = self.info['borg_repository']
        vm_name = self.virtual_machine['name']
        disk_source = disk['source']
        disk_source_path_name = Path(disk_source).stem
        disk_source_file_name = disk_source_path_name.split("/")[-1]
        disk_name = disk['device']

        print(f'[{vm_name}] Creating borg archive for disk {disk_name}')

        self.info[
            'backup_name'] = f'{disk_name}_{disk_source_file_name}_{calendar.timegm(time.gmtime())}'

        if "pool_id" in self.virtual_machine:
            connector = connectors.filter_connector_by_id(
                pool.filter_pool_by_id(self.virtual_machine["pool_id"]).connector_id)
            disk_source = make_path(
                "/mnt", cs_manage_vm.listStorage(connector, disk)["id"], disk_source_path_name)

        cmd = f"""borg create \
        --log-json \
        --progress \
        {make_path(repository, vm_name)}::{self.info['backup_name']} \
        {disk_source}"""

        process = subprocess.Popen(
            cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        while True:
            process.stdout.flush()
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            elif not output and process.poll() is not None:
                break

        print(f'[{vm_name}] Borg archive successfully created for {disk_name}')

    def blockcommit(self, disk):
        vm_name = self.virtual_machine['name']
        kvm_manage_snapshot.blockCommit(
            self.info['vm_info'], self.info['host_info'], disk)
        print(
            f"[{vm_name}] Disk {disk['device']} has been successfully blockcommited")

    def delete_snapshot(self):
        vm_name = self.virtual_machine['name']
        kvm_manage_snapshot.deleteSnapshot(
            self.info['vm_info'], self.info['host_info'])
        print(f'[{vm_name}] Snapshot {vm_name}.snap has been successfully deleted')

    def remove_snapshot_file(self, disk):
        vm_name = self.virtual_machine['name']
        disk_name = disk['device']
        disk_source = f"""{Path(disk['source']).stem}.snap"""
        if os.path.exists(disk_source):
            os.remove(disk_source)
            print(
                f"[{vm_name}] Successfully removed snapshot file '{disk_source}' for disk {disk_name}")

    def borg_prune(self, disk):
        disk_name = disk['device']
        vm_repository_path = make_path(
            self.info['borg_repository'], self.vm_name)
        command = f'borg prune --keep-daily 30 --prefix "{disk_name}" {vm_repository_path}'
        subprocess.run(command.split(), check=True)

        for disk in self.virtual_machine['storage']:
            if ".snap" in disk['source']:
                print(
                    f"[{self.virtual_machine['name']}] Warning: Disk file in use is a snapshot file !")
                print(
                    f"[{self.virtual_machine['name']}] Trying to blockcommit snapshot file to {disk['source']}...")
                try:
                    self.blockcommit(
                        self.info['vm_info'], self.info['host_info'], disk)
                    print(
                        f"[{self.virtual_machine['name']}] Successfully blockcommited {disk['device']}")
                    try:
                        self.remove_snapshot_file(disk)
                        print(
                            f"[{self.virtual_machine['name']}] Snapshot file has been deleted")
                    except Exception:
                        raise ValueError(
                            f"[{self.virtual_machine['name']}] Unable to remove snapshot file. Manual action required")
                except Exception:
                    print(
                        f"[{self.virtual_machine['name']}] Unable to blockcommit file {disk['source']} for disk {disk['device']}. Manual action may be required")

    def send_result(self):
        return self.info['backup_name']

    def delete_archive(self, payload):
        repository = self.info['borg_repository']
        command = f'borg delete {make_path(repository, payload["target"]["name"])}::{payload["selected_backup"]["name"]}'
        request = self.remote_request(command)
        self.process_rc(request)


def borg_list_backup(virtual_machine, repository):
    try:
        # Starting ssh access
        command = f"borg list --json {make_path(repository, virtual_machine)}"
        request = subprocess.run(command.split(), capture_output=True)
        result = ""
        if request.returncode == 2:
            if 'lock' in request.stderr.decode("utf-8"):
                result = '{"archives": [], "state": "locked"}'
            else:
                result = '{"archives": [], "state": "unlocked"}'
        else:
            result = request.stdout.decode("utf-8")
            print(result)
        return result
    except ValueError as err:
        print(err.args[0])
        raise


def borg_backup_info(virtual_machine, repository, backup_name):
    try:
        # Starting ssh access
        command = f"borg info --json {make_path(repository, virtual_machine)}::{backup_name}"
        request = subprocess.run(command.split(), capture_output=True)
        result = ""
        if request.returncode == 2:
            print(request.stdout)
            if 'lock' in request.stderr.decode("utf-8"):
                result = '{"archive": [], "state": "locked"}'
            else:
                print(request.stdout)
                result = f'{"archive": [], "error": "{request.stdout.decode("utf-8")}"}'
        else:
            result = request.stdout.decode("utf-8")
            result = json.loads(result)
            result = result['archives'][0]['stats']
        return result
    except ValueError as err:
        print(err.args[0])
        raise


def borg_list_repository(virtual_machine, repository):
    try:
        # Starting ssh access
        command = f"borg info --json {make_path(repository, virtual_machine)}"
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

# def borg_list_backedup_vm():
#   try:
#     result = os.listdir(borgserver_CS_repositorypath)
#     return result
#   except Exception as e:
#     print(e)
#     raise e

# def delete_repository(self, repository):
#   command = f'borg delete {make_path(borgserver_CS_repositorypath, repository)}'
#   print(command)
#   stdin, stdout, stderr = self.borgSSH.exec_command(command)
#   stdin.write('YES' + '\n')
#   if stdout.channel.recv_exit_status() == 2:
#     for line in iter(stderr.readline, ""):
#       reason = ''
#       reason += line
#     print(reason)
#   else:
#     for line in iter(stdout.readline, ""):
#       output += line
#     print(output)
