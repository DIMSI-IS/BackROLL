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

# SSH Module Imports
import paramiko
import select
# Other imports
from fastapi.encoders import jsonable_encoder
from sqlmodel import Session, select
# Misc
import os
from re import search

from app import database
from app.database import Hosts
from app.routes import host


def get_ssh_client(hostname, username):
  key_filename = os.path.expanduser("~/.ssh/id")

  client = paramiko.SSHClient()
  client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
  client.connect(
    hostname=hostname,
    username=username,
    key_filename=key_filename,
  )
  return client


def init_ssh_connection(host_id, ip_address, username):
  try:
    client = get_ssh_client(
      hostname=ip_address,
      username=username,
    )
    client.close()
  except Exception as e:
    raise ValueError("Connection to hypervisor has failed")

  host.filter_host_by_id(host_id)
  try:
    engine = database.init_db_connection()
  except Exception as e:
    raise ValueError(e)

  with Session(engine) as session:
    statement = select(Hosts).where(Hosts.id == host_id)
    results = session.exec(statement)
    data_host = results.one()
    data_host.ssh = 1
    data_host.username = username
    session.add(data_host)
    session.commit()
    session.refresh(data_host)
  return {'state': 'SUCCESS'}


def remove_key(ip_address, username):
  comment = "BackROLL"

  try:
    client = get_ssh_client(
      hostname=ip_address,
      username=username,
    )
    command = f'sed -i "/{comment}/d" ~/.ssh/authorized_keys'
    client.exec_command(command)
    client.close()
  except Exception as e:
    raise ValueError(e)
