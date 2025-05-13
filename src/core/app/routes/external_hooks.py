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

from fastapi import HTTPException, Depends
from pydantic import BaseModel, Json
from sqlmodel import Session, select
from fastapi.encoders import jsonable_encoder

from app.initialized import fastapi_app
from app.initialized import celery_app

from app import auth
from app import database
from app.database import ExternalHooks
from app.database import Policies
from app.hooks import notification_sender
from app.patch import ensure_uuid


class items_create_external_hook(BaseModel):
    name: str
    value: str

    class Config:
        schema_extra = {
            "example": {
                "name": "my notification method name",
                "value": "webhook url",
            }
        }


@celery_app.task(name="Filter external hook by id")
def get_hook_by_id(hook_id):
    try:
        engine = database.init_db_connection()
    except Exception as exc:
        raise ValueError(exc) from exc
    try:
        with Session(engine) as session:
            statement = select(ExternalHooks).where(
                ExternalHooks.id == ensure_uuid(hook_id))
            results = session.exec(statement)
            pool = results.one()
            if not pool:
                raise ValueError(f"External hook with id {hook_id} not found")
        return pool
    except Exception as exc:
        raise ValueError(exc) from exc


@celery_app.task(name="Create external_hook")
def api_create_external_hook(name, value):
    try:
        engine = database.init_db_connection()
    except Exception as exc:
        raise ValueError(exc) from exc
    try:
        new_external_hook = ExternalHooks(name=name, value=value)
        with Session(engine) as session:
            session.add(new_external_hook)
            session.commit()
            session.refresh(new_external_hook)
        return new_external_hook
    except Exception as exc:
        raise ValueError(exc) from exc


@celery_app.task(name="Read external_hook")
def api_read_external_hook():
    try:
        engine = database.init_db_connection()
    except Exception as exc:
        raise ValueError(exc) from exc
    records = []
    with Session(engine) as session:
        statement = select(ExternalHooks)
        results = session.exec(statement)
        for external_hook in results:
            records.append(external_hook)
    return jsonable_encoder(records)


@celery_app.task(name="Update external_hook")
def api_update_external_hook(hook_id, name, value):
    try:
        engine = database.init_db_connection()
    except Exception as exc:
        raise ValueError("Unable to connect to database.") from exc
    with Session(engine) as session:
        statement = select(ExternalHooks).where(
            ExternalHooks.id == ensure_uuid(hook_id))
        results = session.exec(statement)
        data_external_hook = results.one()
    if not data_external_hook:
        raise ValueError(f"External hook with id {hook_id} not found")
    try:
        if name:
            data_external_hook.name = name
        if value:
            data_external_hook.value = value
        with Session(engine) as session:
            session.add(data_external_hook)
            session.commit()
            session.refresh(data_external_hook)
        return jsonable_encoder(data_external_hook)
    except Exception as exc:
        print(exc)
        raise ValueError(exc) from exc


@celery_app.task(name="Delete external_hook")
def api_delete_external_hook(hook_id):
    try:
        engine = database.init_db_connection()
    except Exception as exc:
        raise ValueError(exc) from exc

    records = []
    with Session(engine) as session:
        statement = select(Policies).where(
            Policies.externalhook == ensure_uuid(hook_id))
        results = session.exec(statement)
        for hook in results:
            records.append(hook)
        if len(records) > 0:
            raise ValueError(
                "One or more policies are attached to this external_hook")
    try:
        external_hook = get_hook_by_id(hook_id)
        with Session(engine) as session:
            session.delete(external_hook)
            session.commit()
        return {"state": "SUCCESS"}
    except Exception as exc:
        raise ValueError(exc) from exc


@fastapi_app.post("/api/v1/externalhooks", status_code=201)
def create_external_hook(
    item: items_create_external_hook, identity: Json = Depends(auth.valid_token)
):
    name = item.name
    value = item.value
    return api_create_external_hook(name, value)


@fastapi_app.get("/api/v1/externalhooks", status_code=202)
def read_external_hook(_: Json = Depends(auth.valid_token)):
    task = api_read_external_hook.delay()
    return {"Location": fastapi_app.url_path_for("retrieve_task_status", task_id=task.id)}


@fastapi_app.patch("/api/v1/externalhooks/{hook_id}", status_code=200)
def update_external_hook(
    hook_id,
    item: items_create_external_hook,
    _: Json = Depends(auth.valid_token),
):
    try:
        uuid_obj = UUID(hook_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=404, detail="Given uuid is not valid") from exc
    name = item.name
    value = item.value
    return api_update_external_hook(hook_id, name, value)


@fastapi_app.get("/api/v1/externalhooks/{hook_id}/test", status_code=200)
def test_external_hook(hook_id, _: Json = Depends(auth.valid_token)):
    notification_sender.test(hook_id)
    return {"state": "SUCCESS"}


@fastapi_app.delete("/api/v1/externalhooks/{hook_id}", status_code=200)
def delete_external_hook(hook_id, identity: Json = Depends(auth.valid_token)):
    try:
        uuid_obj = UUID(hook_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Given uuid is not valid")

    if not hook_id:
        raise HTTPException(status_code=404, detail="Pool not found")
    return api_delete_external_hook(hook_id)
