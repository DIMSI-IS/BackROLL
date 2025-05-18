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
import shutil
import os
from uuid import UUID
from app.patch import ensure_uuid
from fastapi import HTTPException, Depends
from pydantic import BaseModel, Json
from sqlmodel import Session, select
from fastapi.encoders import jsonable_encoder

from app.initialized import fastapi_app

from app.initialized import celery_app

from app import auth
from app import database
from app.database import Hosts
from app.database import Pools
from app.database import Policies
from app.database import Storage


class items_storage(BaseModel):
    name: str
    path: str

    class Config:
        schema_extra = {
            "example": {
                "name": "example_storage",
                "path": "/path/to/my/storage_backend"
            }
        }


def retrieveStoragePathsFromDb():
    engine = database.init_db_connection()

    storagePaths = []
    # Get all storage define in storage bdd
    with Session(engine) as session:
        storagePathsRequest = select(Storage)
        storagePathsFromDb = session.exec(storagePathsRequest)
        for path in storagePathsFromDb:
            storagePaths.append(path)
    return storagePaths


def retrieveStoragePathFromHostBackupPolicy(virtual_machine_info):
    engine = database.init_db_connection()

    try:
        with Session(engine) as session:
            if 'host' in virtual_machine_info:
                # Find host linked to vm
                statement = select(Hosts).where(
                    Hosts.id == ensure_uuid(virtual_machine_info['host']))
                results = session.exec(statement)
                host = results.one()
                if not host:
                    raise ValueError(
                        f"Host with id {virtual_machine_info['host']} not found")
                # Find pool linked to host (KVM)
                statement = select(Pools).where(
                    Pools.id == ensure_uuid(host.pool_id))
                results = session.exec(statement)
                pool = results.one()
                if not pool:
                    raise ValueError(
                        f"Pool with id {host_info['pool_id']} not found")
            else:
                # Find pool linked to vm (CS)
                statement = select(Pools).where(
                    Pools.id == ensure_uuid(virtual_machine_info["pool_id"]))
                results = session.exec(statement)
                pool = results.one()
                if not pool:
                    raise ValueError(
                        f"Pool with id {virtual_machine_info['pool_id']} not found")
            # Find policy linked to pool
            statement = select(Policies).where(
                Policies.id == ensure_uuid(pool.policy_id))
            results = session.exec(statement)
            policy = results.one()
            if not policy:
                raise ValueError(f"Policy with id {pool.policy_id} not found")
            # Find policy linked to pool
            statement = select(Storage).where(
                Storage.id == ensure_uuid(policy.storage))
            results = session.exec(statement)
            storage = results.one()
            if not storage:
                raise ValueError(f"Storage with id {policy.storage} not found")
        return storage.to_json()
    except Exception as e:
        raise ValueError(e)


def filter_storage_by_id(storage_id):
    engine = database.init_db_connection()

    try:
        with Session(engine) as session:
            statement = select(Storage).where(
                Storage.id == ensure_uuid(storage_id))
            results = session.exec(statement)
            storage = results.one()
            if not storage:
                raise ValueError(f'Storage with id {storage_id} not found')
        return storage
    except Exception as e:
        raise ValueError(e)


@celery_app.task(name='create storage')
def api_create_storage(name, path):
    engine = database.init_db_connection()

    try:
        new_storage = Storage(name=name, path=path)
        with Session(engine) as session:
            session.add(new_storage)
            session.commit()
            session.refresh(new_storage)
        return new_storage
    except Exception as e:
        raise ValueError(e)


@celery_app.task(name='Update storage')
def api_update_storage(storage_id, name, path):
    engine = database.init_db_connection()

    with Session(engine) as session:
        statement = select(Storage).where(
            Storage.id == ensure_uuid(storage_id))
        results = session.exec(statement)
        data_storage = results.one()
    if not data_storage:
        raise ValueError(f'Storage with id {storage_id} not found')
    try:
        if name:
            data_storage.name = name
        if path:
            data_storage.path = path
        with Session(engine) as session:
            session.add(data_storage)
            session.commit()
            session.refresh(data_storage)
        return jsonable_encoder(data_storage)
    except Exception as e:
        print(e)
        raise ValueError(e)


@celery_app.task(name='Delete storage')
def api_delete_storage(storage_id):
    engine = database.init_db_connection()

    records = []
    with Session(engine) as session:
        statement = select(Policies).where(
            Policies.storage == ensure_uuid(storage_id))
        results = session.exec(statement)
        for policy in results:
            records.append(policy)
        print(records)
        if len(records) > 0:
            raise HTTPException(
                status_code=409, detail='One or more policies are linked to this storage.')
    try:
        storage = filter_storage_by_id(storage_id)
        with Session(engine) as session:
            session.delete(storage)
            session.commit()
        return {'state': 'SUCCESS'}
    except Exception as e:
        raise ValueError(e)


@celery_app.task(name='List registered storage')
def retrieve_storage():
    engine = database.init_db_connection()

    records = []
    with Session(engine) as session:
        statement = select(Storage)
        results = session.exec(statement)
        for storage in results:
            records.append(storage)
    result = jsonable_encoder(records)
    for item in result:
        try:
            usage_info = shutil.disk_usage(item['path'])
            d = usage_info._asdict()
            dct = dict(d)
            item['info'] = dct
        except:
            item['info'] = None
    return jsonable_encoder(result)


@fastapi_app.get('/api/v1/storage', status_code=202)
def list_storage(identity: Json = Depends(auth.valid_token)):
    task = retrieve_storage.delay()
    return {'Location': fastapi_app.url_path_for('retrieve_task_status', task_id=task.id)}


@fastapi_app.post('/api/v1/storage', status_code=201)
def create_storage(item: items_storage, identity: Json = Depends(auth.valid_token)):
    name = item.name
    path = item.path
    return api_create_storage(name, path)


@fastapi_app.patch("/api/v1/storage/{storage_id}", status_code=200)
def update_storage(storage_id, item: items_storage, identity: Json = Depends(auth.valid_token)):
    try:
        uuid_obj = UUID(storage_id)
    except ValueError:
        raise HTTPException(status_code=404, detail='Given uuid is not valid')
    name = item.name
    path = item.path
    return api_update_storage(storage_id, name, path)


@fastapi_app.delete('/api/v1/storage/{storage_id}', status_code=200)
def delete_storage(storage_id: str, identity: Json = Depends(auth.valid_token)):
    try:
        uuid_obj = UUID(storage_id)
    except ValueError:
        raise HTTPException(status_code=404, detail='Given uuid is not valid')
    if not storage_id:
        raise HTTPException(status_code=404, detail='Pool not found')
    return api_delete_storage(storage_id)
