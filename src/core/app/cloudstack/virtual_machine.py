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

from cs import CloudStack
from app.cloudstack import endpoint
import eventlet

def get_vm():
  cs = endpoint.cs_admin()
  try:
    cscmd = cs.listvirtual_machines(listall=True)
    return cscmd
  except Exception as e:
    print(e)
    pass

def start_vm(identity):
  cs = endpoint.cs_admin()
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
      ddata = e.response.json()
      k,val = ddata.popitem()
      status_code = e.error
      error_message = "HTTP {0} response from CloudStack.\nErrorcode {1}: {2}"
      fmt = error_message.format(e.error['errorcode'], e.error['cserrorcode'], e.error['errortext'])
      errorcode = str(Exception(fmt)).split(':')[1]
      result = {'data':[{'errortext': errorcode}]}
      return result

def stop_vm(identity):
  cs = endpoint.cs_admin()
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
      ddata = e.response.json()
      k,val = ddata.popitem()
      status_code = e.error
      error_message = "HTTP {0} response from CloudStack.\nErrorcode {1}: {2}"
      fmt = error_message.format(e.error['errorcode'], e.error['cserrorcode'], e.error['errortext'])
      errorcode = str(Exception(fmt)).split(':')[1]
      result = {'data':[{'errortext': errorcode}]}
      return result