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

def getDisk(virtual_machine, hypervisor):
  conn = kvm_connection.kvm_connection(hypervisor)
  json = {'id': virtual_machine['id'], 'name': virtual_machine['name'], 'disk_list': []}
  dom = conn.lookupByID(virtual_machine['id'])
  raw_xml = dom.XMLDesc(0)
  xml = minidom.parseString(raw_xml)
  disk_types = xml.getElementsByTagName('disk')
  for disk_type in disk_types:
      if (disk_type.getAttribute('device') != 'cdrom'):
          disk_nodes = disk_type.childNodes
          for disk_node in disk_nodes:
              if disk_node.nodeName[0:1] != '#':
                  if (disk_node.nodeName == 'target'):
                      for attr in disk_node.attributes.keys():
                          if (disk_node.attributes[attr].name == 'dev'):
                              device = disk_node.attributes[attr].value
                  if (disk_node.nodeName == 'source'):
                      for attr in disk_node.attributes.keys():
                          if (disk_node.attributes[attr].name == 'file'):
                              source = disk_node.attributes[attr].value
          json['disk_list'].append({'device': device, 'source': source})
  conn.close()
  return json