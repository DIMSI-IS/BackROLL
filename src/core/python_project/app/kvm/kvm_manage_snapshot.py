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

from __future__ import print_function
# KVM Connection Module Imports
from app.kvm import kvm_connection, disk_safety


def get_snapshot(vm_info, host_info):
    conn = kvm_connection.kvm_connection(host_info)
    json = {'id': vm_info['id'], 'name': vm_info['name'], 'snapshot': []}
    dom = conn.lookupByName(vm_info['name'])
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
        dom = conn.lookupByName(virtual_machine['name'])
        flags = 208
        dom.snapshotCreateXML(
            snapshot_xml,
            flags
        )
    except Exception as snapshot_error:
        conn.close()
        if 'guest agent is not configured' in str(snapshot_error):
            raise ValueError(
                f"The QEMU guest agent of {virtual_machine['name']} is not available: BackROLL freezes the file system "
                "before the snapshot and needs it. Install qemu-guest-agent in the machine and add the virtio-serial "
                f"channel (org.qemu.guest_agent.0) to its definition. ({snapshot_error})") from snapshot_error
        raise snapshot_error
    conn.close()


def deleteSnapshot(virtual_machine, hypervisor):
    try:
        conn = kvm_connection.kvm_connection(hypervisor)
        dom = conn.lookupByName(virtual_machine['name'])
        snapshot = dom.snapshotLookupByName(
            f"""{virtual_machine['name']}.snap""")
        flags = 2
        snapshot.delete(flags)
    except Exception as snapshot_error:
        conn.close()
        raise snapshot_error
    conn.close()


def open_domain(virtual_machine, hypervisor):
    """The connection to the hypervisor and the libvirt domain of the machine. The caller closes the connection."""
    conn = kvm_connection.kvm_connection(hypervisor)
    try:
        return conn, conn.lookupByName(virtual_machine['name'])
    except Exception:
        conn.close()
        raise


def blockCommit(virtual_machine, hypervisor, disk_info):
    """Commits the overlay of a disk into its base file and puts the machine back on the base file.

    Raises BackupStateError when this could not be checked. A job that does not end is left running (see
    disk_safety): the overlay is never cancelled, nor deleted, from here."""
    conn, dom = open_domain(virtual_machine, hypervisor)
    try:
        base = disk_safety.base_of(disk_info["source"])
        disk_safety.commit_and_pivot(
            dom, disk_info["device"], base, disk_safety.overlay_of(disk_info["source"]))
    finally:
        conn.close()
