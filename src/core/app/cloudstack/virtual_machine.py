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

from app.cloudstack import endpoint
import eventlet

def start_vm(connector, identity):
  cs = endpoint.cloudstack_connector(connector)
  try:
      cscmd = cs.startVirtualMachine(id=identity)
      jobID = cscmd["jobid"]
      jobquery = cs.queryAsyncJobResult(jobid=jobID)
      while jobquery["jobstatus"] == 0:
          eventlet.sleep(1)
          jobquery = cs.queryAsyncJobResult(jobid=jobID)
      if jobquery["jobstatus"] == 1:
          return
      elif jobquery["jobstatus"] == 2:
          raise ValueError(jobquery)

  except Exception as e:
      error_message = "HTTP {0} response from CloudStack.\nErrorcode {1}: {2}"
      fmt = error_message.format(e.error['errorcode'], e.error['cserrorcode'], e.error['errortext'])
      errorcode = str(Exception(fmt)).split(':')[1]
      result = {'data':[{'errortext': errorcode}]}
      return result

def stop_vm(connector, identity):
  cs = endpoint.cloudstack_connector(connector)
  try:
      cscmd = cs.stopVirtualMachine(id=identity)
      jobID = cscmd["jobid"]
      jobquery = cs.queryAsyncJobResult(jobid=jobID)
      while jobquery["jobstatus"] == 0:
          eventlet.sleep(1)
          jobquery = cs.queryAsyncJobResult(jobid=jobID)
      if jobquery["jobstatus"] == 1:
          return
      elif jobquery["jobstatus"] == 2:
          raise ValueError(jobquery)

  except Exception as e:
      error_message = "HTTP {0} response from CloudStack.\nErrorcode {1}: {2}"
      fmt = error_message.format(e.error['errorcode'], e.error['cserrorcode'], e.error['errortext'])
      errorcode = str(Exception(fmt)).split(':')[1]
      result = {'data':[{'errortext': errorcode}]}
      return result

def listStorage(connector, storage):
    cs = endpoint.cloudstack_connector(connector)
    cloudstack_storage_list = cs.listStoragePools(listall=True, id=storage["storageid"])
    if "storagepool" in cloudstack_storage_list:
      return cloudstack_storage_list["storagepool"][0]
    else: return []

def listPoweredOffVms(connector):
  try:
    cs = endpoint.cloudstack_connector(connector)
    cloudstack_vm_list = cs.listVirtualMachines(listall=True, state="Stopped")
    if "virtualmachine" in cloudstack_vm_list:
      for vm in cloudstack_vm_list['virtualmachine']:
        vm["uuid"] = vm["id"]
        vm["id"] = -1
        vm["cpus"] = vm["cpunumber"]
        vm["mem"] = vm["memory"] * 1024
        vm["name"] = vm["instancename"]
        vm["pool_id"] = str(connector.pool_id)
        vm["connector_id"] = str(connector.id)
        for e in ['nic', 'details', 'guestosid', 'ostypeid', 'zoneid', 'userid', 'serviceofferingid', 'serviceofferingname', 'osdisplayname', 'pooltype']:
          vm.pop(e)
        print
      return cloudstack_vm_list['virtualmachine']
    else: return []
  except Exception as e:
    print(e)
    print("Unable to connect to Cloudstack. Likely is a timeout issue or wrong url/credentials.")
    return []
  
def listAllVms(connector):
  try:
    cs = endpoint.cloudstack_connector(connector)
    cloudstack_vm_list = cs.listVirtualMachines(listall=True)
    if "virtualmachine" in cloudstack_vm_list:
      for vm in cloudstack_vm_list['virtualmachine']:
        vm["uuid"] = vm["id"]
        vm["id"] = -1
        vm["cpus"] = vm["cpunumber"]
        vm["mem"] = vm["memory"] * 1024
        vm["name"] = vm["instancename"]
        vm["pool_id"] = str(connector.pool_id)
        vm["connector_id"] = str(connector.id)
        for e in ['nic', 'details', 'guestosid', 'ostypeid', 'zoneid', 'userid', 'serviceofferingid', 'serviceofferingname', 'osdisplayname', 'pooltype']:
          vm.pop(e)
        print
      return cloudstack_vm_list['virtualmachine']
    else: return []
  except Exception as e:
    print(e)
    print("Unable to connect to Cloudstack. Likely is a timeout issue or wrong url/credentials.")
    return []
    
    
def getDisk(connector, virtualmachine):
    cs = endpoint.cloudstack_connector(connector)
    cloudstack_disk_list = cs.listVolumes(virtualmachineid=virtualmachine["uuid"])
    if "volume" in cloudstack_disk_list:
      for disk in cloudstack_disk_list['volume']:
        disk["device"] = disk["name"]
        disk["source"] = disk["path"]
      return cloudstack_disk_list["volume"]
    else:
      return []