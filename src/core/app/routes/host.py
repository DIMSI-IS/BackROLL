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

#!/usr/bin/env python
import os
import uuid as uuid_pkg
from typing import Optional
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field, Json
from sqlmodel import Session, select
from fastapi.encoders import jsonable_encoder
from celery import Celery, states
from celery.exceptions import Ignore

from app import app

from app import celery

from app import auth
from app import database
from app.database import Hosts
from app.database import Pools
from app import ssh
from app.routes import virtual_machine

class items_create_host(BaseModel):
  hostname: str
  tags: Optional[str] = None
  ip_address: str
  pool_id: uuid_pkg.UUID
  class Config:
      schema_extra = {
          "example": {
              "name": "example_hostname",
              "tags": "production_server",
              "ip_address": "192.168.1.200",
              "pool_id": "679b3dd4-a39f-11ec-b909-0242ac120002"
          }
      }

class items_connect_host(BaseModel):
  host_id: str
  ip_address: str
  username: str
  password: Optional[str] = None
  class Config:
      schema_extra = {
          "example": {
              "host_id": "6ce2e0e4-a39f-11ec-b909-0242ac120002",
              "ip_address": "192.168.1.200",
              "username": "root",
              "password": "mystrongpassword"
          }
      }

@celery.task(name='filter_host_by_id')
def filter_host_by_id(host_id):
  try:
    engine = database.init_db_connection()
    with Session(engine) as session:
      statement = select(Hosts).where(Hosts.id == host_id)
      results = session.exec(statement)
      host = results.first()
    if not host:
      reason = f'Host with id {host_id} not found'
      raise HTTPException(status_code=404, detail=reason)
    return host
  except Exception as e:
    raise HTTPException(status_code=500, detail=jsonable_encoder(e))


@celery.task(name='filter_host_list_by_pool')
def filter_host_list_by_pool(host_list, pool_id):
  filtered_host_list = []
  for host in host_list:
    if host['pool_id'] == pool_id:
      filtered_host_list.append(host)
  return filtered_host_list

def api_create_host(hostname, tags, ipaddress, poolid):
  try:
    engine = database.init_db_connection()
  except Exception as e:
    raise HTTPException(status_code=500, detail=jsonable_encoder(e))
  with Session(engine) as session:
    statement = select(Pools).where(Pools.id == poolid)
    results = session.exec(statement)
    pool = results.first()
    if not pool:
      reason = f'Pool with id {str(poolid)} not found'
      raise HTTPException(status_code=404, detail=reason)
  try:
    new_host = Hosts(hostname=hostname, tags=tags, ipaddress=ipaddress, pool_id=poolid)
    with Session(engine) as session:
        session.add(new_host)
        session.commit()
        session.refresh(new_host)
        return new_host
  except Exception as e:
    print(e)
    raise HTTPException(status_code=500, detail=jsonable_encoder(e))

@celery.task(name='List registered hosts')
def retrieve_host():
  try:
    engine = database.init_db_connection()
  except Exception as e:
    raise HTTPException(status_code=500, detail=jsonable_encoder(e))
  try:
    records = []
    with Session(engine) as session:
        statement = select(Hosts)
        results = session.exec(statement)
        for host in results:
          records.append(host)
    for host in records:
      HOST_UP  = True if os.system(f"nc -z -w 1 {host.ipaddress} 22 > /dev/null") == 0 else False
      if HOST_UP:
          pingstatus = 'Reachable'
      else:
          pingstatus = 'Unreachable'
      host.state = pingstatus
    return jsonable_encoder(records)
  except Exception as e:
    raise HTTPException(status_code=500, detail=jsonable_encoder(e))

def api_delete_host(host_id):
  ssh_status = 0
  try:
    engine = database.init_db_connection()
  except Exception as e:
    raise HTTPException(status_code=500, detail=jsonable_encoder(e))
  with Session(engine) as session:
    statement = select(Hosts).where(Hosts.id == host_id)
    results = session.exec(statement)
    host = results.first()
    if not host:
      reason = f'Host with id {host_id} not found'
      raise HTTPException(status_code=404, detail=reason)
    HOST_UP  = True if os.system(f"nc -z -w 1 {host.ipaddress} 22 > /dev/null") == 0 else False
    if (host.ssh == 1) and HOST_UP:
      ssh.remove_key(host.ipaddress, host.username)
    session.delete(host)
    session.commit()
  return {'state': 'SUCCESS'}


def first_ssh_connection(host_id, ip_address, username, password):
  if password:
    return ssh.deploy_key(ip_address, username, password)
  else:
    return ssh.try_ssh_connection(host_id, ip_address, username)

def getSSHPubKey():
  try:
    pubkey = os.popen('cat ~/.ssh/id_rsa.pub').read()
    return {'state': 'SUCCESS', 'info': {'public_key': pubkey}}
  except Exception as e:
    raise HTTPException(status_code=404, detail='Unable to retrieve appliance public key')

@app.post("/api/v1/hosts", status_code=201)
def create_host(item: items_create_host, identity: Json = Depends(auth.valid_token)):
  name = item.hostname
  tags = item.tags
  ip_address = item.ip_address
  pool_id = item.pool_id
  return api_create_host(name, tags, ip_address, pool_id)

@app.get("/api/v1/hosts", status_code=202)
# def list_hosts():
def list_hosts(identity: Json = Depends(auth.valid_token)):

    task = retrieve_host.delay()
    return {'Location': app.url_path_for('retrieve_task_status', task_id=task.id)}

@app.delete('/api/v1/hosts/{host_id}', status_code=200)
def delete_host(host_id, identity: Json = Depends(auth.valid_token)):
  try:
      uuid_obj = uuid_pkg.UUID(host_id)
  except ValueError:
      raise HTTPException(status_code=404, detail='Given uuid is not valid')
  return api_delete_host(host_id)

@app.post('/api/v1/connect/{host_id}', status_code=200)
def init_host_ssh_connection(host_id, item: items_connect_host, identity: Json = Depends(auth.valid_token)):
  host_id = item.host_id
  ip_address = item.ip_address
  username = item.username
  password = item.password
  return first_ssh_connection(host_id, ip_address, username, password)

@app.get("/api/v1/publickeys", status_code=200)
def list_ssh_public_keys(identity: Json = Depends(auth.valid_token)):
  return getSSHPubKey()