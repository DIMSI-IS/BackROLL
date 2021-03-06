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

# MySQL Module Imports
import mysql.connector
# SSH Module Imports
import paramiko
import select
# Other imports
from fastapi import FastAPI, HTTPException
from fastapi.encoders import jsonable_encoder
from sqlmodel import Session, select
# Misc
import os
from re import search

from app import database
from app.routes import host

def try_ssh_connection(host_id, ip_address, username):
  client = paramiko.SSHClient()
  client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

  keyfile = os.path.expanduser('~/.ssh/id_rsa.pub')

  try:
    client.connect(
      hostname=ip_address,
      username=username,
      key_filename = keyfile,
    )
    client.close()
  except Exception as e:
    raise HTTPException(status_code=400, detail=jsonable_encoder(e))

  host.filter_host_by_id(host_id)
  try:
    engine = database.init_db_connection()
  except Exception as e:
    raise HTTPException(status_code=500, detail=jsonable_encoder(e))

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

def deploy_key(host_id, ip_address, username, password):
  get_key = os.popen('cat ~/.ssh/id_rsa.pub').read()
  client = paramiko.SSHClient()
  client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
  try:
    client.connect(
        hostname=ip_address,
        username=username,
        password=password
    )
  except Exception as e:
    raise HTTPException(status_code=400, detail=jsonable_encoder(e))
    client.exec_command('mkdir -p ~/.ssh/')
    client.exec_command('echo "%s" >> ~/.ssh/authorized_keys' % get_key)
    client.exec_command('chmod 644 ~/.ssh/authorized_keys')
    client.exec_command('chmod 700 ~/.ssh/')
    client.close()
  host.filter_host_by_id(host_id)
  try:
    engine = database.init_db_connection()
  except Exception as e:
    raise HTTPException(status_code=500, detail=jsonable_encoder(e))

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
  try:
    hostname = "backroll-appliance"
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        hostname=ip_address,
        username=username,
    )
    cmd = f'sed -i "/{hostname}/d" ~/.ssh/authorized_keys'
    client.exec_command(cmd)
    client.close()
    return
  except Exception as e:
    raise ValueError(e)