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

# Libvirt dependencies Imports
from xml.dom import minidom
import re
import libvirt

from app.kvm import kvm_connection
# from app.borg import borg_core
# from app.routes import virtual_machine

def retrieve_virtualmachine(host):
    try:
      conn = kvm_connection.kvm_connection(host)
    except:
      raise ValueError(f"Unable to connect to host with id {host['id']}")
    domains = conn.listAllDomains(0)
    domain_list = []
    if len(domains) != 0:
        for domain in domains:

          is_cloudstack_instance = False

          # Check that VM is managed by CloudStack
          raw_xml = domain.XMLDesc(0)
          xml = minidom.parseString(raw_xml)
          sysbios_xml  = xml.getElementsByTagName('system')
          if len(sysbios_xml) > 0:
            smbiosEntries  = sysbios_xml[0].getElementsByTagName('entry')
            for smbiosEntry in smbiosEntries:
              if "cloudstack" in str(smbiosEntry.firstChild.nodeValue).lower():
                is_cloudstack_instance = True
          
          # Ignoring VMs managed by CloudStack and name starting with r-/s- as these are VR or SystemVM
          if is_cloudstack_instance and not re.search("^((?!^r-)(?!^v-)(?!^s-).)*$", domain.name()): continue
          
          else:
            instance = {}
            instance['id'] = domain.ID()
            instance['uuid'] = domain.UUIDString()
            instance['name'] = domain.name()
            state, maxmem, mem, cpus, cput = domain.info()
            instance['mem'] = mem
            instance['cpus'] = cpus
            instance['host'] = host['id']
            instance['host_tag'] = host['tags']
            instance['cloudstack_instance'] = is_cloudstack_instance


                
            state, reason = domain.state()
            if state == libvirt.VIR_DOMAIN_NOSTATE:
                instance['state'] = 'No_State'
            elif state == libvirt.VIR_DOMAIN_RUNNING:
                instance['state'] = 'Running'
            elif state == libvirt.VIR_DOMAIN_BLOCKED:
                instance['state'] = 'Blocked'
            elif state == libvirt.VIR_DOMAIN_PAUSED:
                instance['state'] = 'Paused'
            elif state == libvirt.VIR_DOMAIN_SHUTDOWN:
                instance['state'] = 'Shutdown'
            elif state == libvirt.VIR_DOMAIN_SHUTOFF:
                instance['state'] = 'Shutoff'
            elif state == libvirt.VIR_DOMAIN_CRASHED:
                instance['state'] = 'Crashed'
            elif state == libvirt.VIR_DOMAIN_PMSUSPENDED:
                instance['state'] = 'Suspended'
            else:
                instance['state'] = 'Unknown'

            domain_list.append(instance)

        conn.close()
        return domain_list
      
def stop_vm(virtual_machine, hypervisor):
  # TODO
  print("#### DEBUG ####")
  print("#### stop_vm ####")
  print("#### DEBUG ####")
  try:
    conn = kvm_connection.kvm_connection(hypervisor)

    # TODO
    # dom = conn.lookupByID(virtual_machine['id'])
    dom = conn.lookupByName("debian12-minimal")

    dom.destroy()
  except Exception as stopvm_error:
    raise stopvm_error
  
def start_vm(virtual_machine, hypervisor):
  # TODO
  print("#### DEBUG ####")
  print("#### start_vm ####")
  print("#### DEBUG ####")
  try:
    conn = kvm_connection.kvm_connection(hypervisor)

    # TODO
    # dom = conn.lookupByID(virtual_machine['id'])
    dom = conn.lookupByName("debian12-minimal")

    dom.destroy()
  except Exception as stopvm_error:
    raise stopvm_error