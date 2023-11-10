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

from __future__ import print_function
# KVM Connection Module Imports
from app.kvm import kvm_connection
import time

def get_snapshot(vm_info, host_info):
    conn = kvm_connection.kvm_connection(host_info)
    json = {'id': vm_info['id'], 'name': vm_info['name'], 'snapshot': []}
    dom = conn.lookupByID(vm_info['id'])
    flag = dom.hasCurrentSnapshot()
    json['snapshot'] = int(flag)
    conn.close()
    return json

def generate_xmlSnapshot(vm_name, vm_storage):
  sub_xml_disk = ""  
  for disk in vm_storage:
    sub_xml_disk += f"""
        <disk name='{disk["device"]}' snapshot='external'>
          <source file='{disk['source'].replace(".snap", "")}.snap'/>
        </disk>
    """
  
  SNAPSHOT_XML_TEMPLATE = f"""
    <domainsnapshot>
      <name>{vm_name}.snap</name>
      <disks>
        {sub_xml_disk}
      </disks>
    </domainsnapshot>
  """
  return SNAPSHOT_XML_TEMPLATE

def createSnapshot(virtual_machine, hypervisor, snapshot_xml):
  try:
    conn = kvm_connection.kvm_connection(hypervisor)
    dom = conn.lookupByID(virtual_machine['id'])
    flags = 208
    test = dom.snapshotCreateXML(
      snapshot_xml,
      flags
    )
    print(f"test = {test}")
    print("snapshot ok")
  except Exception as snapshot_error:
    print("snapshot ko")
    conn.close()
    raise snapshot_error
  conn.close()  

def deleteSnapshot(virtual_machine, hypervisor):
  try:
    conn = kvm_connection.kvm_connection(hypervisor)
    dom = conn.lookupByID(virtual_machine['id'])
    snapshot = dom.snapshotLookupByName(f"""{virtual_machine['name']}.snap""")
    flags = 2
    snapshot.delete(flags)
  except Exception as snapshot_error:
    conn.close()
    raise snapshot_error
  conn.close()
  
def blockCommit(virtual_machine, hypervisor, disk_info):
  try:
    conn = kvm_connection.kvm_connection(hypervisor)
    dom = conn.lookupByID(virtual_machine['id'])
    flags = 6
    dom.blockCommit(
      disk_info["device"],
      disk_info["source"].replace(".snap", ""),
      f'{disk_info["source"].replace(".snap", "")}.snap',
      0,
      flags
    )
    blockJob = dom.blockJobInfo(disk_info["device"])
    while blockJob['cur'] < blockJob['end']:
      time.sleep(2)
      blockJob = dom.blockJobInfo(disk_info["device"])
    dom.blockJobAbort(disk_info["device"], 2)
  except Exception as blockcommit_error:
    conn.close()
    raise blockcommit_error
  conn.close()