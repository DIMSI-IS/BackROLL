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
# SSH Module Imports
import paramiko
import libvirt
# Libvirt dependencies Imports
import sys
from xml.dom import minidom
# KVM Connection Module Imports
from app.kvm import kvm_connection

def get_snapshot(vm_info, host_info):
    conn = kvm_connection.kvm_connection(host_info)
    json = {'id': vm_info['id'], 'name': vm_info['name'], 'snapshot': []}
    dom = conn.lookupByID(vm_info['id'])
    flag = dom.hasCurrentSnapshot()
    json['snapshot'] = int(flag)
    conn.close()
    return json