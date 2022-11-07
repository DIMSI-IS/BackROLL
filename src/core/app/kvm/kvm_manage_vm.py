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
          if re.search("^((?!^r-)(?!^v-)(?!^s-).)*$", domain.name()):

            instance = {}

            instance['id'] = domain.ID()
            instance['uuid'] = domain.UUIDString()
            instance['name'] = domain.name()

            state, maxmem, mem, cpus, cput = domain.info()
            instance['mem'] = mem
            instance['cpus'] = cpus

            instance['host'] = host['id']
            instance['host_tag'] = host['tags']

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
  try:
    conn = kvm_connection.kvm_connection(hypervisor)
    dom = conn.lookupByID(virtual_machine['id'])
    dom.destroy()
  except Exception as stopvm_error:
    raise stopvm_error
  
def start_vm(virtual_machine, hypervisor):
  try:
    conn = kvm_connection.kvm_connection(hypervisor)
    dom = conn.lookupByID(virtual_machine['id'])
    dom.destroy()
  except Exception as stopvm_error:
    raise stopvm_error