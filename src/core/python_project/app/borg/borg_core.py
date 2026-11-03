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
import os.path
from os import path
from pathlib import Path
import calendar
import time
import re
import shlex
import shutil

from app.routes import pool
from app.routes import connectors

# KVM custom module import
from app.kvm import kvm_manage_snapshot, disk_safety
from app.kvm.disk_safety import BackupStateError

# CS custom module import
from app.cloudstack import virtual_machine as cs_manage_vm

from app.patch import make_path
from app import cleanup, disk_state, file_backup, notifier, shell
from app.ssh import connect_ssh


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
        # True once the machine was put on its overlays by this run: only then is there something to bring back.
        self.snapshot_created = False

        if 'ip_address' in self.info and 'username' in self.info:
            self.host_ssh, _ = connect_ssh(
                self.info['ip_address'], self.info['username'])

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
        # The repository exists when it has its configuration: an empty folder left by an initialization that
        # failed is not one.
        if os.path.isfile(os.path.join(vm_repository_path, 'config')):
            # Borg repo exists
            print(f'[{self.vm_name}] A Borg repository for this VM has been found')
        else:
            # Borg repo doesn't exist
            print(
                f'[{self.vm_name}] Borg repository for this VM doesn\'t exist. Creating a new one')
            Path(vm_repository_path).mkdir(parents=True, exist_ok=True)
            # Initializing borg repository
            print(f'[{self.vm_name}] Initializing the new borg repo')
            shell.subprocess_run(
                f"borg init --encryption none {shlex.quote(vm_repository_path)}")
        print(f'[{self.vm_name}] Borg repository setup is OK')

    def check_repository_lock(self):
        self.vm_name = self.info['name']
        print(f'[{self.vm_name}] Checking borg repository lock status')
        # Check if borg repo is locked
        vm_repository_path = make_path(
            self.info['borg_repository'], self.vm_name)
        try:
            shell.subprocess_run(
                f"borg list --lock-wait 300 {shlex.quote(vm_repository_path)}")
            print(f'[{self.vm_name}] Borg repository is unlocked, job will continue')
        except Exception as error:
            print(f'[{self.vm_name}] Borg repository is locked, job will stop')
            if 'lock' in str(error).lower():
                raise ValueError(
                    f'The repository of {self.vm_name} is locked by another operation: wait for it to end, or unlock '
                    f'the repository from the page of the machine if nothing is running. ({error})') from error
            raise

    def checking_files_trace(self, disk):
        if os.path.exists(f'{disk["source"].replace(".snap", "")}.snap'):
            return True
        else:
            return False

    def check_if_snapshot(self):
        vm_state = kvm_manage_snapshot.get_snapshot(
            self.info['vm_info'], self.info['host_info'])
        if vm_state['snapshot'] == 1:
            print(
                f"[{self.virtual_machine['name']}] A snapshot has been detected !")
            return True
        else:
            print(f"[{self.virtual_machine['name']}] No snapshot detected")
            return False

    def create_snapshot(self):
        vm_name = self.virtual_machine['name']
        print(f'[{vm_name}] Snapshotting virtual machines disks')
        snapshot_xml = kvm_manage_snapshot.generate_xmlSnapshot(
            vm_name, self.virtual_machine['storage'])
        self.snapshot_created = True
        kvm_manage_snapshot.createSnapshot(
            self.info['vm_info'], self.info['host_info'], snapshot_xml)
        for disk in self.virtual_machine['storage']:
            self.step(disk, disk_state.SNAPSHOT_CREATED)

    def manage_backing_file(self, disk):
        repository = self.info['borg_repository']
        vm_name = self.virtual_machine['name']
        print(f"[{vm_name}] Getting information about disk at {disk['source']}")
        json_output = shell.subprocess_run(
            f"qemu-img info --output=json {disk['source']}")
        qemu_img_info = json.loads(json_output)
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

    def resolve_disk_source(self, disk):
        """The path of a disk on the BackROLL side."""
        disk_source = disk['source']
        if "pool_id" in self.virtual_machine:
            connector = connectors.filter_connector_by_id(
                pool.filter_pool_by_id(self.virtual_machine["pool_id"]).connector_id)
            disk_source = make_path(
                "/mnt", cs_manage_vm.listStorage(connector, disk)["id"], Path(disk_source).stem)
        return disk_source

    def backup_files(self, policy):
        """Backs up the folders and files chosen in the policy. The disks are backed up
        whatever happens here: a failure is reported in the log, it does not fail the job."""
        paths = file_backup.parse_paths(policy.file_paths)
        if not paths:
            return
        vm_name = self.virtual_machine['name']
        try:
            print(f'[{vm_name}] Backing up {len(paths)} folder(s) or file(s)')
            repository = make_path(self.info['borg_repository'], vm_name)
            images = [self.resolve_disk_source(disk) for disk in self.virtual_machine['storage']]
            results = file_backup.backup_paths(repository, images, paths, calendar.timegm(time.gmtime()))
            for result in results:
                if result['status'] == 'success':
                    print(f"[{vm_name}] {result['path']} backed up in {result['archive']}")
                else:
                    print(f"[{vm_name}] Warning: {result['path']} could not be backed up. {result['error']}")
            file_backup.prune(repository, {
                "daily": policy.retention_day, "weekly": policy.retention_week,
                "monthly": policy.retention_month, "yearly": policy.retention_year})
        except Exception as exception:
            print(f'[{vm_name}] Warning: the backup of the folders and files failed. {exception}')

    def create_archive(self, disk):
        repository = self.info['borg_repository']
        vm_name = self.virtual_machine['name']
        disk_source = disk['source']
        disk_source_path_name = Path(disk_source).stem
        # The name of an archive is used in commands and in the API: nothing but plain characters.
        disk_source_file_name = re.sub(r"[^A-Za-z0-9._-]+", "-", disk_source_path_name.split("/")[-1])
        disk_name = disk['device']

        print(f'[{vm_name}] Creating borg archive for disk {disk_name}')

        self.info[
            'backup_name'] = f'{disk_name}_{disk_source_file_name}_{calendar.timegm(time.gmtime())}'

        disk_source = self.resolve_disk_source(disk)

        shell.subprocess_popen(f"""borg create \
            --log-json \
            --progress \
            --lock-wait 300 \
            {shlex.quote(make_path(repository, vm_name))}::{shlex.quote(self.info['backup_name'])} \
            {shlex.quote(disk_source)}""")

        print(f'[{vm_name}] Borg archive successfully created for {disk_name}')
        self.step(disk, disk_state.BORG_DONE)

    def blockcommit(self, disk):
        """Commits the overlay of the disk and checks, in the XML of the machine, that it is back on its base file."""
        vm_name = self.virtual_machine['name']
        self.step(disk, disk_state.COMMIT_STARTED)
        kvm_manage_snapshot.blockCommit(
            self.info['vm_info'], self.info['host_info'], disk)
        self.step(disk, disk_state.VERIFIED)
        print(
            f"[{vm_name}] Disk {disk['device']} has been successfully blockcommited")

    def delete_snapshot(self):
        vm_name = self.virtual_machine['name']
        kvm_manage_snapshot.deleteSnapshot(
            self.info['vm_info'], self.info['host_info'])
        print(
            f'[{vm_name}] Snapshot {vm_name}.snap has been successfully deleted')

    # -- the safety of the disks (the rules are in app/kvm/disk_safety.py)

    def step(self, disk, step, message=None):
        """Records where a disk is in its backup. `disk` is a disk of the machine or the name of its device."""
        device = disk['device'] if isinstance(disk, dict) else disk
        return disk_state.set_step(self.info['vm_info'].get('uuid') or self.vm_name, self.vm_name, device, step, message)

    def attention(self, device, message):
        """The disk may not be in the state that a backup needs: the next backups of the machine stop."""
        print(f"[{self.vm_name}] NEEDS ATTENTION, disk {device}: {message}")
        if self.step(device, disk_state.NEEDS_ATTENTION, message):
            # Told once, to the hook of the policy of the machine, when the disk starts to wait.
            notifier.send_to_policy_hook(self.info['vm_info'], notifier.attention_message(self.vm_name, device, message),
                                         notifier.attention_blocks(self.vm_name, device, message))

    def path_exists(self, path):
        """Looked at on the hypervisor when it is reachable: it is the one that knows what its machine uses."""
        if hasattr(self, 'host_ssh'):
            return self.remote_request(f"test -e {shlex.quote(path)}")['rc'] == 0
        return os.path.exists(path)

    def preflight(self):
        """Before the snapshot: refuses a machine whose disks are not as a backup needs them. Repairs nothing.

        The machine must not wait for an administrator, be on an overlay file, have a block job running or leave
        an overlay file on the storage. A refused machine is put in NEEDS_ATTENTION (and stays so until cleared)."""
        uuid = self.info['vm_info'].get('uuid') or self.vm_name
        waiting = disk_state.attention_of(uuid)
        if waiting:
            raise BackupStateError(
                f"NEEDS ATTENTION: {self.vm_name} is blocked until an administrator clears it "
                f"(disk {waiting[0]['disk']}: {waiting[0]['message']})")
        conn, dom = kvm_manage_snapshot.open_domain(self.info['vm_info'], self.info['host_info'])
        try:
            for disk in self.virtual_machine['storage']:
                try:
                    disk_safety.preflight(dom, disk['device'])
                    overlay = disk_safety.overlay_of(disk['source'])
                    if self.path_exists(overlay):
                        raise BackupStateError(
                            f"{disk['device']}: the file {overlay} is left on the storage, nothing is deleted by itself")
                except BackupStateError as error:
                    self.attention(disk['device'], str(error))
                    raise BackupStateError(f"NEEDS ATTENTION: {error}") from error
                self.step(disk, disk_state.PRECHECK_OK)
        finally:
            conn.close()
        # The record of an old snapshot that left no file: it is only the record, the disks are on their base files.
        if self.check_if_snapshot():
            self.delete_snapshot()
        print(f"[{self.vm_name}] Pre-flight checks done")

    def recover(self):
        """After a failed backup: puts the machine back on its disks if the run had put it on overlays.

        What can not be brought back is left as it is and reported (NEEDS_ATTENTION). No file is deleted here."""
        if not self.snapshot_created:
            return
        try:
            conn, dom = kvm_manage_snapshot.open_domain(self.info['vm_info'], self.info['host_info'])
        except Exception as error:
            for disk in self.virtual_machine['storage']:
                self.attention(disk['device'], f"the hypervisor could not be asked after the failure ({error})")
            return
        try:
            failed = disk_safety.recover_disks(dom, self.virtual_machine['storage'], self.attention)
        finally:
            conn.close()
        if not failed:
            try:
                self.delete_snapshot()
            except Exception as error:
                print(f"[{self.vm_name}] The record of the snapshot could not be removed. {error}")

    def remove_snapshot_file(self, disk):
        """Puts a leftover overlay of the disk aside when nothing uses it. It is renamed, never deleted."""
        vm_name = self.virtual_machine['name']
        overlay = disk_safety.overlay_of(disk['source'])
        if not self.path_exists(overlay):
            return
        conn, dom = kvm_manage_snapshot.open_domain(self.info['vm_info'], self.info['host_info'])
        try:
            moved = disk_safety.safe_remove(dom, overlay, self.remote_request)
        except BackupStateError as error:
            self.attention(disk['device'], str(error))
            raise
        finally:
            conn.close()
        print(f"[{vm_name}] The leftover file '{overlay}' of disk {disk['device']} was put aside as '{moved}'")

    def cleanup_after_backup(self):
        """Right after the backup of the machine: see the cleaning of the storage."""
        for disk in self.virtual_machine.get('storage', []):
            self.step(disk, disk_state.CLEANED)
        cleanup.after_backup(self.info['borg_repository'], self.vm_name)

    def borg_prune(self, disk, backup_policy):
        disk_name = disk['device']

        vm_repository_path = make_path(
            self.info['borg_repository'], self.vm_name)
        if backup_policy.retention_day > 0 or backup_policy.retention_week > 0 or backup_policy.retention_month > 0 or backup_policy.retention_year > 0:
            command = f'borg prune' \
                f'{f" --keep-daily {backup_policy.retention_day}" if backup_policy.retention_day > 0 else ""}' \
                f'{f" --keep-weekly {backup_policy.retention_week}" if backup_policy.retention_week > 0 else ""}' \
                f'{f" --keep-monthly {backup_policy.retention_month}" if backup_policy.retention_month > 0 else ""}' \
                f'{f" --keep-yearly {backup_policy.retention_year}" if backup_policy.retention_year > 0 else ""}' \
                f' --lock-wait 300 --glob-archives {shlex.quote(disk_name + "_*")} {shlex.quote(vm_repository_path)}'

            try:
                shell.subprocess_run(command)
            except Exception as exception:
                # The archive of the disk is made: a retention that could not run (a lock, for instance) must not
                # fail the backup nor stop the backup of the other disks. The next backup applies it again.
                print(f"[{self.vm_name}] Warning: the old backups of {disk_name} could not be removed. {exception}")
            else:
                # Borg frees the space of the deleted backups only with this step.
                compact_repository(vm_repository_path)

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
        # Formatting may a space after :: !
        target = shlex.quote(make_path(repository, payload["target"]["name"]))
        archive = shlex.quote(payload["selected_backup"]["name"])
        command = f'borg delete {target}::{archive}'
        request = self.remote_request(command)
        if request.returncode == 2:
            print(request.stderr.decode("utf-8"))
            raise ValueError(request.stderr.decode("utf-8"))


def borg_list_backup(virtual_machine, repository):
    try:
        # Starting ssh access
        try:
            result = shell.subprocess_run(
                f"borg list --json {shlex.quote(make_path(repository, virtual_machine))}")
        except shell.ShellException as exception:
            if exception.exit_code == 2:
                if 'lock' in exception.stderr:
                    result = '{"archives": [], "state": "locked"}'
                else:
                    result = '{"archives": [], "state": "unlocked"}'
            else:
                raise
        return result
    except ValueError as err:
        print(err.args[0])
        raise


def compact_repository(repository_path):
    """Frees the space of the backups that were deleted. A failure is a warning: the backup itself is done."""
    try:
        shell.subprocess_run(f"borg compact --lock-wait 300 {shlex.quote(str(repository_path))}")
    except Exception as exception:
        print(f"Warning: the space could not be freed in {repository_path}. {exception}")


def borg_backup_info(virtual_machine, repository, backup_name):
    try:
        # Starting ssh access
        try:
            result = shell.subprocess_run(
                f"borg info --json {shlex.quote(make_path(repository, virtual_machine))}::{shlex.quote(backup_name)}")
        except shell.ShellException as exception:
            if exception.exit_code == 2:
                if 'lock' in exception.stderr:
                    result = '{"archive": [], "state": "locked"}'
                else:
                    # TODO Not consistent with borg info duplicated code.
                    result = f'{"archive": [], "error": "{exception.stderr}"}'
            else:
                raise
        result = json.loads(result)
        return result['archives'][0]['stats']
    except ValueError as err:
        print(err.args[0])
        raise


def borg_list_repository(virtual_machine, repository):
    try:
        # Starting ssh access
        try:
            result = shell.subprocess_run(
                f"borg info --json {shlex.quote(make_path(repository, virtual_machine))}")
        except shell.ShellException as exception:
            if exception.exit_code == 2:
                if 'lock' in exception.stderr:
                    result = '{"archives": [], "state": "locked"}'
                else:
                    result = '{"archives": [], "state": "unlocked"}'
            else:
                # TODO everywhere raise or raise exception ?
                raise
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
