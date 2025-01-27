# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
##
# http://www.apache.org/licenses/LICENSE-2.0
##
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

#!/usr/bin/env python
import os
from uuid import UUID
from app.patch import ensure_uuid
import paramiko
from typing import Optional
from fastapi import Depends, HTTPException
from pydantic import BaseModel, Json
from sqlmodel import Session, select
from fastapi.encoders import jsonable_encoder

from app import app
from app import celery

from app import auth
from app import database
from app.database import Hosts
from app.database import Pools
from app import ssh
from app.routes import virtual_machine
from app import shell


class items_create_host(BaseModel):
    hostname: str
    tags: Optional[str] = None
    ip_address: str
    pool_id: UUID

    class Config:
        schema_extra = {
            "example": {
                "name": "example_hostname",
                "tags": "production_server",
                "ip_address": "192.168.1.200",
                "pool_id": "679b3dd4-a39f-11ec-b909-0242ac120002",
            }
        }


class items_update_host(BaseModel):
    hostname: Optional[str] = None
    tags: Optional[str] = None
    ip_address: Optional[str] = None
    pool_id: Optional[UUID] = None

    class Config:
        schema_extra = {
            "example": {
                "name": "example_hostname",
                "tags": "production_server",
                "ip_address": "192.168.1.200",
            }
        }


class items_connect_host(BaseModel):
    ip_address: str
    username: str

    class Config:
        schema_extra = {
            "example": {
                "ip_address": "192.168.1.200",
                "username": "root"
            }
        }


@celery.task(name='filter_host_by_id')
def filter_host_by_id(host_id):
    try:
        engine = database.init_db_connection()
        with Session(engine) as session:
            statement = select(Hosts).where(Hosts.id == ensure_uuid(host_id))
            results = session.exec(statement)
            host = results.first()
        if not host:
            raise ValueError(f'Host with id {host_id} not found')
        return host
    except Exception as e:
        raise ValueError(e)


@celery.task(name='filter_host_list_by_pool')
def filter_host_list_by_pool(host_list, pool_id):
    filtered_host_list = []
    for host in host_list:
        if host['pool_id'] == pool_id:
            filtered_host_list.append(host)
    return filtered_host_list


def api_create_host(item):
    try:
        engine = database.init_db_connection()
    except Exception as e:
        raise ValueError(e)
    with Session(engine) as session:
        statement = select(Pools).where(Pools.id == ensure_uuid(item.pool_id))
        results = session.exec(statement)
        pool = results.first()
        if not pool:
            raise Exception(f'Pool with id {str(item.pool_id)} not found')
    try:
        new_host = Hosts(hostname=item.hostname, tags=item.tags,
                         ipaddress=item.ip_address, pool_id=item.pool_id)
        with Session(engine) as session:
            session.add(new_host)
            session.commit()
            session.refresh(new_host)
            return new_host
    except Exception as e:
        raise ValueError(e)


def api_update_host(host_id, hostname, tags, ipaddress, pool_id):
    try:
        engine = database.init_db_connection()
    except:
        raise ValueError('Unable to connect to database.')
    with Session(engine) as session:
        statement = select(Hosts).where(Hosts.id == ensure_uuid(host_id))
        results = session.exec(statement)
        data_host = results.one()
    if not data_host:
        raise ValueError(f'Host with id {host_id} not found')
    if pool_id:
        with Session(engine) as session:
            statement = select(Pools).where(Pools.id == ensure_uuid(pool_id))
            results = session.exec(statement)
            pool = results.first()
            if not pool:
                raise ValueError(f'Pool with id {str(pool_id)} not found')
    try:
        if hostname:
            data_host.hostname = hostname
        if ipaddress:
            data_host.ipaddress = ipaddress
        if pool_id:
            data_host.pool_id = pool_id
        if tags:
            data_host.tags = tags
        with Session(engine) as session:
            session.add(data_host)
            session.commit()
            session.refresh(data_host)
        return jsonable_encoder(data_host)
    except Exception as e:
        print(e)
        raise ValueError(e)


@celery.task(name='List registered hosts')
def retrieve_host():
    try:
        engine = database.init_db_connection()
    except Exception as e:
        raise ValueError(e)
    try:
        records = []
        with Session(engine) as session:
            statement = select(Hosts)
            results = session.exec(statement)
            for host in results:
                records.append(host)
        for host in records:
            try:
                shell.os_system(f"nc -z -w 1 {host.ipaddress} 22 > /dev/null")
                host.state = 'Reachable'
            except:
                host.state = 'Unreachable'
        return jsonable_encoder(records)
    except Exception as e:
        raise ValueError(e)


def api_delete_host(host_id):
    ssh_status = 0
    try:
        engine = database.init_db_connection()
    except Exception as e:
        raise ValueError(e)
    with Session(engine) as session:
        statement = select(Hosts).where(Hosts.id == ensure_uuid(host_id))
        results = session.exec(statement)
        host = results.first()
        if not host:
            raise ValueError(f'Host with id {host_id} not found')
        is_host_up = True if shell.os_system(
            f"nc -z -w 1 {host.ipaddress} 22 > /dev/null", check=False) == 0 else False
        if (host.ssh == 1) and is_host_up:
            ssh.remove_key(host.ipaddress, host.username)
        session.delete(host)
        session.commit()
    return {'state': 'SUCCESS'}


def getSSHPubKey():
    try:
        pubkey = shell.os_popen('cat /root/.ssh/id_rsa.pub')
        return {'state': 'SUCCESS', 'info': {'public_key': pubkey}}
    except Exception as e:
        raise ValueError('Unable to retrieve appliance public key')


@app.post("/api/v1/hosts", status_code=201)
def create_host(item: items_create_host, identity: Json = Depends(auth.valid_token)):
    return api_create_host(item)


@app.get("/api/v1/hosts", status_code=202)
# def list_hosts():
def list_hosts(identity: Json = Depends(auth.valid_token)):

    task = retrieve_host.delay()
    return {'Location': app.url_path_for('retrieve_task_status', task_id=task.id)}


@app.patch("/api/v1/hosts/{host_id}", status_code=200)
def update_host(host_id, item: items_update_host, identity: Json = Depends(auth.valid_token)):
    try:
        uuid_obj = UUID(host_id)
    except ValueError:
        raise HTTPException(status_code=404, detail='Given uuid is not valid')
    name = item.hostname
    tags = item.tags
    ip_address = item.ip_address
    pool_id = item.pool_id
    return api_update_host(host_id, name, tags, ip_address, pool_id)


@app.delete('/api/v1/hosts/{host_id}', status_code=200)
def delete_host(host_id, identity: Json = Depends(auth.valid_token)):
    try:
        uuid_obj = UUID(host_id)
    except ValueError:
        raise HTTPException(status_code=404, detail='Given uuid is not valid')
    return api_delete_host(host_id)


@app.post('/api/v1/connect/{host_id}', status_code=200)
def init_host_ssh_connection(host_id, item: items_connect_host, identity: Json = Depends(auth.valid_token)):
    print("init ssh  " + shell.os_popen("cat /etc/hostname"))
    ip_address = item.ip_address
    username = item.username
    return ssh.init_ssh_connection(host_id, ip_address, username)


@app.get("/api/v1/publickeys", status_code=200)
def list_ssh_public_keys(identity: Json = Depends(auth.valid_token)):
    return getSSHPubKey()
