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

import sys
import libvirt
from xml.dom import minidom

from app.kvm import kvm_connection

def retrieve_uuid(virtual_machine, hypervisor):
  conn = None
  try:
      conn = kvm_connection.kvm_connection(hypervisor)
  except libvirt.libvirtError as e:
      print(repr(e), file=sys.stderr)
      exit(1)
  dom = None
  try:
      dom = conn.lookupByID(virtual_machine['id'])
  except libvirt.libvirtError as e:
      print(repr(e), file=sys.stderr)
      exit(1)
  uuid = dom.UUIDString()
  conn.close()
  return uuid