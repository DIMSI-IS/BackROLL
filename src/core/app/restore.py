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
import subprocess
from redis import Redis
from fastapi.encoders import jsonable_encoder
from celery_once import QueueOnce
from app import celery

from app.routes import host
from app.routes import storage
from app.kvm import kvm_list_disk
from app.cloudstack import virtual_machine as cs_vm_command

from app.routes import pool
from app.routes import connectors

# KVM custom module import
from app.kvm import kvm_manage_vm

# CS custom module import
from app.cloudstack import virtual_machine as cs_manage_vm

@celery.task(name='VM_Restore_Disk', bind=True, max_retries=3, base=QueueOnce)
def restore_disk_vm(self, info, backup_name, storage, mode):
#def restore_disk_vm(self, info, backup_name):

  if not info:
    raise Exception("Virtual machine not found to process restore")
  #mode = "single"
  #storage = "test"
  print("DEBUG $$$ vm uuid: " + info["uuid"])
  for x in info:
    print(x)
  try:
    redis_instance = Redis(host='redis', port=6379)
    unique_task_key = f'''vmlock-{info}'''
    if not redis_instance.exists(unique_task_key):
      #No duplicated key found in redis - target IS NOT locked right now
      redis_instance.set(unique_task_key, "")
      redis_instance.expire(unique_task_key, 5400)
      try:
        if "host" in info:
          # Retrieve VM host info
          host_info = jsonable_encoder(host.filter_host_by_id(info['host']))
          vm_storage_info = kvm_list_disk.getDisk(info, host_info)
        else:
          print("DEBUG POOL ID")
          host_info = None
          connector = connectors.filter_connector_by_id(pool.filter_pool_by_id(info["pool_id"]).connector_id)
          vm_storage_info = cs_manage_vm.getDisk(connector, info)

        if mode == "mounted":
          try:
            print("Debug - go to restore_to_path_task")
            restore_to_path_task(self, info, host_info, storage, backup_name)
          except Exception:
            self.retry(countdown=3**self.request.retries)
        else:
          try:
            print("Debug - go to restore_task")
            restore_task(self, info, host_info, vm_storage_info, backup_name)
          except Exception:
            self.retry(countdown=3**self.request.retries)
      except:
        raise
    else:
      #Duplicated key found in redis - target IS locked right now
      raise ValueError("This task is already running / scheduled")
    redis_instance.delete(unique_task_key)
    print("Debug - restore_disk_vm - start")
  except Exception as e:
    redis_instance.delete(unique_task_key)
    # potentially log error?
    raise e

# def restore_task(self, info, hypervisor, disk_list, backup):
def restore_task(self, virtual_machine_info, hypervisor, vm_storage_info, backup_name):
  print("Debug - restore_task - start")    
  vm_storage = storage.retrieveStoragePathFromHostBackupPolicy(virtual_machine_info)
  borg_repository = vm_storage["path"]
  print("DEBUG borg_repository " + borg_repository)

  try:

    disk_device = backup_name.split('_')[0]

    # Remove existing files inside restore folder
    command = f"rm -rf {borg_repository}restore/{virtual_machine_info['name']}"
    subprocess.run(command.split())  

    # Create temporary folder to extract borg archive
    command = f"mkdir -p {borg_repository}restore/{virtual_machine_info['name']}"
    subprocess.run(command.split())

    # Go into directory
    os.chdir(f"{borg_repository}restore/{virtual_machine_info['name']}")
    
    connector = None

    if "pool_id" in virtual_machine_info:
      connector = connectors.filter_connector_by_id(pool.filter_pool_by_id(virtual_machine_info["pool_id"]).connector_id)
    else:
      filtered_pool = pool.filter_pool_by_id(hypervisor["pool_id"])
      connector = connectors.filter_connector_by_id(filtered_pool.connector_id)

    try:
      # Extract selected borg archive
      cmd = f"""borg extract --sparse --strip-components=2 {borg_repository}{virtual_machine_info['name']}::{backup_name}"""
      process = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
      while True:
        process.stdout.flush()
        output = process.stdout.readline()
        if output == '' and process.poll() is not None:
          break
        elif not output and process.poll() is not None:
          break
      # Loop through VM's disks to find filedisk
      for disk in vm_storage_info:
        if disk['device'] == disk_device:
          break
      virtual_machine_disk = disk["source"]

      # Build path based on disk source path
      if "host" in virtual_machine_info:
        # For a KVM vm
        path = virtual_machine_disk.split("/")
        del path[-1]
        del path[0]
        kvm_storagepath = ""
        for item in path:
          kvm_storagepath += f"/{item}"
        kvm_storagepath += "/"
      else:
        # For a powered off CS vm
        kvm_storagepath = "/mnt/" + cs_manage_vm.listStorage(connector, disk)["id"] + "/"
      

      if virtual_machine_disk == None:
        raise ValueError('Unable to match backup with existing diskfile. Aborting restore job')
      
      if "host" in virtual_machine_info:
        virtual_machine_diskName = virtual_machine_disk.split('/')[-1]
      else:
        virtual_machine_diskName = disk["path"]

      if "host" in virtual_machine_info:
        # Power off guest VM
        if virtual_machine_info['cloudstack_instance']:
          cs_vm_command.stop_vm(connector, virtual_machine_info['uuid'])
        else:
          kvm_manage_vm.stop_vm(virtual_machine_info, hypervisor)

      try:
        subprocess.run(['cp', virtual_machine_diskName, f"{kvm_storagepath}{virtual_machine_diskName}-tmp"], check = True)
        # os.system(f"cp {virtual_machine_diskName} {kvm_storagepath}{virtual_machine_diskName}-tmp")

        # Fix chmod ownership of new qcow2 filedisk
        subprocess.run(['chmod', '644', f"{kvm_storagepath}{virtual_machine_diskName}-tmp"], check = True)
        # os.system(f"chmod 644 {kvm_storagepath}{virtual_machine_diskName}-tmp")

        # Replace disk by extracted backup
        subprocess.run(['mv', f"{kvm_storagepath}{virtual_machine_diskName}-tmp", f"{kvm_storagepath}{virtual_machine_diskName}"], check = True)

        # Remove temporary folder used to extract borg archive
        subprocess.run(['rm', "-rf", f"{borg_repository}restore/{virtual_machine_info['name']}"])
        # os.system(f"rm -rf {borg_repository}restore/{virtual_machine_info['name']}")
      except Exception as e:
        raise e

      if "host" in virtual_machine_info:
        # Power on guest VM
        if virtual_machine_info['cloudstack_instance']:
          cs_vm_command.start_vm(connector, virtual_machine_info['uuid'])
        else:
          kvm_manage_vm.start_vm(virtual_machine_info, hypervisor)

    except Exception as e:
      # Remove restore artifacts
      command = f"rm -rf {borg_repository}restore/{virtual_machine_info['name']}"
      request = subprocess.run(command.split())
      raise e
    print("Debug - restore_task - end")
  except Exception as e:

    # Remove restore artifacts
    try:
      command = f"rm -rf {borg_repository}restore/{virtual_machine_info['name']}"
      request = subprocess.run(command.split())
    except Exception as err:
      print(err)

    raise e

# def restore_task_mounted(self, info, hypervisor, disk_list, backup):
def restore_to_path_task(self, virtual_machine_info, hypervisor, storage_path, backup_name):

  print("restore_to_path_task")

  borg_repository = storage_path + "/"

  print("borg repo: " + borg_repository)

  try:

    disk_device = backup_name.split('_')[0]

    print("disk-device: " + disk_device)

    print("vm name: " + virtual_machine_info['name'])

    # Remove existing files inside restore folder
    command = f"rm -rf {borg_repository}restore/{virtual_machine_info['name']}"
    subprocess.run(command.split())  

    # Create temporary folder to extract borg archive
    command = f"mkdir -p {borg_repository}restore/{virtual_machine_info['name']}"
    subprocess.run(command.split())

    # Go into directory
    os.chdir(f"{borg_repository}restore/{virtual_machine_info['name']}")
    
    connector = None
    pool_id = None

    if "pool_id" in virtual_machine_info:
      pool_id = virtual_machine_info["pool_id"]
    else:
      pool_id = hypervisor["pool_id"]

    print("Pool id : " + pool_id)
    
    connector_id = pool.filter_pool_by_id(pool_id).connector_id
    if connector_id:
      connector = connectors.filter_connector_by_id(connector_id)

    try:
      # Extract selected borg archive
      cmd = f"""borg extract --sparse --strip-components=2 {borg_repository}{virtual_machine_info['name']}::{backup_name}"""
      processBorgExtract = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
      while True:
        processBorgExtract.stdout.flush()
        output = processBorgExtract.stdout.readline()
        if output == '' and processBorgExtract.poll() is not None:
          break
        elif not output and processBorgExtract.poll() is not None:
          break

      # Process each file in extraction directory
      # For each file exec qemu-img info
      # if backing file faire suite algo sinon rien
      rootPath = f"""{borg_repository}{virtual_machine_info['name']}"""
      print(f"rootPath: {rootPath}")

      for filename in os.listdir(borg_repository):
        diskPath = f"""{rootPath}/{filename}"""
        print(f"diskPath: {diskPath}")

        getDiskInfoCmd = f"""qemu-img info {diskPath}"""
        diskInfoData = subprocess.run(getDiskInfoCmd.split(), capture_output=True, shell=True, text=True)
        diskInfo = diskInfoData.stdout
        print(f"diskInfo: {diskInfo}")

        indexBackingFile = diskInfo.find("backing file: ")
        print(f"indexBackingFile: {indexBackingFile}")
        indexFormatSpecificInformation = diskInfo.find("Format specific information")
        print(f"indexFormatSpecificInformation: {indexFormatSpecificInformation}")

        if indexBackingFile > 0:
          backingFileValue = diskInfo[indexBackingFile:indexFormatSpecificInformation]
          print(f"backingFileValue: {backingFileValue}")

          if backingFileValue.len() > 0:
            # Copy backing file in new folder
            #subprocess.run(['cp', backingFileValue, "/mnt/eu-backup-cs/restore/"], check = True)

            cmd = f"""quemu-img rebase \ -f qcow2 \ -u \ -b $new_backing_file_location \ {diskPath}"""
            #subprocess.run(cmd.split())

            cmd = f"""quemu-img info {diskPath}"""
            #subprocess.run(cmd.split())

            #subprocess.run(['rm', diskPath], check = True)

    except:
      raise    

  except Exception as e:

    # Remove restore artifacts
    try:
      command = f"rm -rf {borg_repository}restore/{virtual_machine_info['name']}"
      request = subprocess.run(command.split())
    except Exception as err:
      print(err)

    raise e