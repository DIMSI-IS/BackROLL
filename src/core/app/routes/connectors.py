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
from uuid import UUID
from app.patch import ensure_uuid
from fastapi import HTTPException, Depends
from pydantic import Json
from sqlmodel import Session, select
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Json
from pathlib import Path

from app.initialized import fastapi_app
from app.initialized import celery_app

from app import auth
from app import database

from app.database import Hosts
from app.database import Connectors


class items_create_connector(BaseModel):
    name: str
    url: str
    login: str
    password: str

    class Config:
        schema_extra = {
            "example": {
                "name": "connector.local",
                "url": "http(s)://endpoint.connector.local",
                "login": "username",
                "password": "your secret password"
            }
        }


def filter_connector_by_id(connector_id):
    engine = database.init_db_connection()

    try:
        with Session(engine) as session:
            statement = select(Connectors).where(
                Connectors.id == ensure_uuid(connector_id))
            results = session.exec(statement)
            storage = results.one()
            if not storage:
                raise ValueError(f'Connector with id {connector_id} not found')
        return storage
    except Exception as e:
        raise ValueError(e)


@celery_app.task(name='Update connector')
def api_update_connector(connector_id, name, url, login, password):
    engine = database.init_db_connection()

    with Session(engine) as session:
        statement = select(Connectors).where(
            Connectors.id == ensure_uuid(connector_id))
        results = session.exec(statement)
        data_connector = results.one()
    if not data_connector:
        raise ValueError(f'Connector with id {connector_id} not found')
    try:
        if name:
            data_connector.name = name
        if url:
            data_connector.url = url
        if login:
            data_connector.login = login
        if password:
            data_connector.password = password
        with Session(engine) as session:
            session.add(data_connector)
            session.commit()
            session.refresh(data_connector)
        return jsonable_encoder(data_connector)
    except Exception as e:
        print(e)
        raise ValueError(e)


@celery_app.task(name='create connector')
def api_create_connector(name, url, login, password):
    engine = database.init_db_connection()

    try:
        new_connector = Connectors(
            name=name, url=url, login=login, password=password)
        with Session(engine) as session:
            session.add(new_connector)
            session.commit()
            session.refresh(new_connector)
        return new_connector
    except Exception as e:
        raise ValueError(e)


@celery_app.task(name='list connectors')
def api_retrieve_connectors():
    engine = database.init_db_connection()

    try:
        records = []
        with Session(engine) as session:
            statement = select(Connectors)
            results = session.exec(statement)
            for connector in results:
                records.append(connector)
        return jsonable_encoder(records)
    except Exception as e:
        raise ValueError(e)


@celery_app.task(name='Delete connector')
def api_delete_connector(connector_id):
    engine = database.init_db_connection()

    records = []
    with Session(engine) as session:
        statement = select(Hosts).where(
            Hosts.connector_id == ensure_uuid(connector_id))
        results = session.exec(statement)
        for host in results:
            records.append(host)
        if len(records) > 0:
            raise ValueError('One or more hosts are linked to this connector')
    try:
        connector = filter_connector_by_id(connector_id)
        with Session(engine) as session:
            session.delete(connector)
            session.commit()
        return {'state': 'SUCCESS'}
    except Exception as e:
        raise ValueError(e)


@fastapi_app.post('/api/v1/connectors', status_code=201)
def create_connector(item: items_create_connector, identity: Json = Depends(auth.verify_token)):
    name = item.name
    url = item.url
    login = item.login
    password = item.password
    return api_create_connector(name, url, login, password)


@fastapi_app.get('/api/v1/connectors', status_code=202)
def retrieve_connectors(identity: Json = Depends(auth.verify_token)):
    task = api_retrieve_connectors.delay()
    return {'Location': fastapi_app.url_path_for('retrieve_task_status', task_id=task.id)}


@fastapi_app.patch('/api/v1/connectors/{connector_id}', status_code=200)
def update_connector(connector_id, item: items_create_connector, identity: Json = Depends(auth.verify_token)):
    try:
        uuid_obj = UUID(connector_id)
    except ValueError:
        raise HTTPException(status_code=404, detail='Given uuid is not valid')
    name = item.name
    url = item.url
    login = item.login
    password = item.password
    return api_update_connector(connector_id, name, url, login, password)


@fastapi_app.delete('/api/v1/connectors/{connector_id}', status_code=200)
def delete_connector(connector_id, identity: Json = Depends(auth.verify_token)):
    try:
        uuid_obj = UUID(connector_id)
    except ValueError:
        raise HTTPException(status_code=404, detail='Given uuid is not valid')

    if not connector_id:
        raise HTTPException(status_code=404, detail='Pool not found')
    return api_delete_connector(connector_id)
