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
import json
from uuid import UUID
from app.patch import ensure_uuid
from croniter import croniter
from typing import Optional
from fastapi import Depends, HTTPException, Security, status
from fastapi.encoders import jsonable_encoder
from sqlmodel import Session, select
from pydantic import BaseModel, ConfigDict, Field, Json
from celery import Celery, states, chord
from celery.result import AsyncResult
from celery.schedules import crontab
from redbeat import RedBeatSchedulerEntry

from app.initialized import fastapi_app
from app import auth
from app import database
from app.database import Policies
from app.database import Storage
from app.database import Pools
from app.database import Hosts
from app.logging import logged
from app import file_backup
from app import cleanup

from app.routes import external_hooks

from app.initialized import celery_app as celeryWorker
from app.initialized import celery_app


class retention_settings(BaseModel):
    """How many backups are kept: a key that is not known, or a negative number, is refused with its name."""
    model_config = ConfigDict(extra='forbid')

    day: int = Field(0, ge=0)
    week: int = Field(0, ge=0)
    month: int = Field(0, ge=0)
    year: int = Field(0, ge=0)


class backup_policy_create(BaseModel):
    name: str
    description: Optional[str] = None
    schedule: str
    retention: retention_settings
    storage: UUID
    externalhook: Optional[UUID] = None
    enabled: Optional[bool] = False
    file_paths: Optional[list[str]] = None

    class Config:
        schema_extra = {
            "example": {
                "name": "example_policy",
                "description": "Daily backup routine (at midnight)",
                "schedule": "0 0 * * *",
                "retention_day": "1",
                "retention_week": "1",
                "retention_month": "1",
                "retention_year": "1",
                "storage": "7984bbc7-d202-4603-834f-5d1a5bf0e33e",
                "externalhook": "https://my.example-webhook.com/ud4jf"
            }
        }


class backup_policy_update(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    schedule: Optional[str] = None
    retention: Optional[retention_settings] = None
    storage: Optional[UUID] = None
    externalhook: Optional[UUID] = None
    enabled: Optional[bool] = None
    # None leaves the paths as they are, an empty list removes them.
    file_paths: Optional[list[str]] = None

    class Config:
        schema_extra = {
            "example": {
                "name": "example_policy",
                "description": "Daily backup routine (at midnight)",
                "schedule": "0 0 * * *",
                "retention_day": "1",
                "retention_week": "1",
                "retention_month": "1",
                "retention_year": "1",
                "storage": "7984bbc7-d202-4603-834f-5d1a5bf0e33e",
                "externalhook": "https://my.example-webhook.com/ud4jf"
            }
        }


def filter_policy_by_id(policy_id):
    engine = database.init_db_connection()

    try:
        with Session(engine) as session:
            statement = select(Policies).where(
                Policies.id == ensure_uuid(policy_id))
            results = session.exec(statement)
            policy = results.one()
            if not policy:
                raise ValueError(f'Policy with id {policy_id} not found')
        return policy
    except Exception as e:
        raise ValueError(e)


def check_name_is_free(name, policy_id=None):
    """Two policies with the same name (whatever the case) could not be told apart in the lists and the messages."""
    engine = database.init_db_connection()
    with Session(engine) as session:
        for policy in session.exec(select(Policies)):
            if str(policy.id) != str(policy_id) and policy.name.strip().lower() == name.strip().lower():
                raise HTTPException(status_code=409, detail=f'A policy named "{policy.name}" already exists.')


def checked_file_paths(file_paths):
    if file_paths is None:
        return None
    try:
        return file_backup.validate_paths(file_paths)
    except ValueError as exception:
        raise HTTPException(status_code=400, detail=str(exception))


@celery_app.task(name='create_backup_policy')
def api_create_backup_policy(name, description, schedule, retention, storage, externalhook, file_paths=None):
    engine = database.init_db_connection()

    try:
        new_policy = Policies(name=name, description=description or "", schedule=schedule, retention_day=retention["day"], retention_week=retention[
                              "week"], retention_month=retention["month"], retention_year=retention["year"], storage=storage, externalhook=externalhook,
                              file_paths="\n".join(file_paths) if file_paths else None)
        with Session(engine) as session:
            session.add(new_policy)
            session.commit()
            session.refresh(new_policy)
            return new_policy
    except Exception as e:
        raise ValueError(e)


@celery_app.task(name='delete_backup_policy')
def api_delete_backup_policy(backup_policy_id):
    engine = database.init_db_connection()

    try:
        with Session(engine) as session:
            statement = select(Policies).where(
                Policies.id == ensure_uuid(backup_policy_id))
            results = session.exec(statement)
            policy = results.one()
            if not policy:
                raise ValueError(
                    f'Backup policy with id {backup_policy_id} not found')
            session.delete(policy)
            session.commit()
            return {'state': 'SUCCESS'}
    except Exception as e:
        raise ValueError(e)


@celery_app.task(name='List backup policies')
def retrieve_backup_policies():
    engine = database.init_db_connection()

    try:
        records = []
        with Session(engine) as session:
            statement = select(Policies)
            results = session.exec(statement)
            for policy in results:
                records.append(policy)
        return jsonable_encoder(records)
    except Exception as e:
        raise ValueError(e)


@logged(bounds=False)
def api_update_backup_policy(policy_id, name, description, schedule, retention, storage, externalhook, enabled, logger, file_paths=None):
    engine = database.init_db_connection()

    with Session(engine) as session:
        statement = select(Policies).where(
            Policies.id == ensure_uuid(policy_id))
        data_backup_policy = session.exec(statement).first()

    if not data_backup_policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'backup policy with id {policy_id} not found',
        )
    # Without an answer, the policy keeps its state: editing a policy must not switch its backups off.
    if enabled is None:
        enabled = data_backup_policy.enabled == 1
    task = "Kickstart_Pool_Backup"
    if schedule:
        split_cron = schedule.split()
    else:
        split_cron = data_backup_policy.schedule.split()
    if name:
        policy_name = name
    else:
        policy_name = data_backup_policy.name

    try:
        data_pool = []
        with Session(engine) as session:
            statement = select(Pools).where(
                Pools.policy_id == ensure_uuid(policy_id))
            results = session.exec(statement)
            for pool in results:
                data_pool.append(pool)
    except Exception as e:
        raise ValueError(e)

    if data_backup_policy.enabled == 1:
        if not data_pool:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f'backup policy with id {policy_id} has no pool associated to it',
                headers={"WWW-Authenticate": "Bearer"},
            )
        for pool in data_pool:
            currentPool = pool.to_json()
            unique_task_name = f"{task}-{data_backup_policy.name}-{data_backup_policy.id}-{currentPool['name']}"
            key = f"redbeat:{unique_task_name}"
            entry = None
            try:
                entry = RedBeatSchedulerEntry.from_key(key, app=celery_app)
            except:
                # If the redis volume has been removed.
                # TODO Warning to the user ?
                logger.info("Scheduler entry is absent.")
            if entry is not None:
                try:
                    logger.info("Deleting scheduler entry…")
                    entry.delete()
                except Exception as entry:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=str(entry),
                        headers={"WWW-Authenticate": "Bearer"}
                    ) from entry

    if enabled == True:
        if not data_pool:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f'backup policy with id {policy_id} has no pool associated to it',
                headers={"WWW-Authenticate": "Bearer"}
            )
        for pool in data_pool:
            try:
                data_host = []
                with Session(engine) as session:
                    statement = select(Hosts).where(
                        Hosts.pool_id == ensure_uuid(pool.id))
                    results = session.exec(statement)
                    for host in results:
                        data_host.append(host)
                if not data_host:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f'backup policy with id {policy_id} has one or more empty pool associated to it',
                        headers={"WWW-Authenticate": "Bearer"}
                    )
            except HTTPException:
                # A refusal wanted by the code is sent as it is, with its message, not as an error of the server.
                raise
            except Exception as e:
                raise ValueError(e)
            try:
                currentPool = pool.to_json()
                unique_task_name = f"{task}-{policy_name}-{policy_id}-{currentPool['name']}"
                # Cron counts Sunday as 0 or 7, Celery only as 0; "*", ranges and steps are kept as they are.
                day_of_week = cleanup.celery_day_of_week(split_cron[4])
                cron = crontab(minute=split_cron[0], hour=split_cron[1], day_of_month=split_cron[2],
                               month_of_year=split_cron[3], day_of_week=day_of_week)
                entry = RedBeatSchedulerEntry(
                    unique_task_name, task, cron, args=(currentPool['id'],), app=celery_app)
                entry.save()
            except Exception as e:
                raise ValueError(e)
    try:
        if enabled == True:
            data_backup_policy.enabled = 1
        else:
            data_backup_policy.enabled = 0
        if name:
            data_backup_policy.name = name
        if description:
            data_backup_policy.description = description
        if schedule:
            data_backup_policy.schedule = schedule
        if retention:
            data_backup_policy.retention_day = retention["day"]
            data_backup_policy.retention_week = retention["week"]
            data_backup_policy.retention_month = retention["month"]
            data_backup_policy.retention_year = retention["year"]
        if storage:
            data_backup_policy.storage = storage
        if file_paths is not None:
            data_backup_policy.file_paths = "\n".join(file_paths) or None
        if externalhook is not None:
            external_hooks.get_hook_by_id(externalhook)
            data_backup_policy.externalhook = externalhook
        else:
            data_backup_policy.externalhook = None
        with Session(engine) as session:
            session.add(data_backup_policy)
            session.commit()
            session.refresh(data_backup_policy)
        return jsonable_encoder(data_backup_policy)
    except HTTPException:
        raise
    except Exception as e:
        raise ValueError(e)


@fastapi_app.post("/api/v1/backup_policies", status_code=201)
def create_backup_policy(item: backup_policy_create, identity: Json = Depends(auth.require_editor)):
    engine = database.init_db_connection()

    records = []
    with Session(engine) as session:
        statement = select(Storage).where(
            Storage.id == ensure_uuid(item.storage))
        results = session.exec(statement)
        for policy in results:
            records.append(policy)
        if len(records) < 1:
            reason = f'Specified storage hasn\'t been found'
            raise HTTPException(status_code=404, detail=reason)
    name = item.name
    description = item.description
    schedule = item.schedule
    retention = item.retention.model_dump()
    storage = item.storage
    externalhook = item.externalhook
    file_paths = checked_file_paths(item.file_paths)
    check_name_is_free(name)
    return api_create_backup_policy(name, description, schedule, retention, storage, externalhook, file_paths)


@fastapi_app.get("/api/v1/backup_policies", status_code=202)
def list_backup_policies(identity: Json = Depends(auth.verify_token)):
    task = retrieve_backup_policies.delay()
    return {'Location': fastapi_app.url_path_for('retrieve_task_status', task_id=task.id)}


@fastapi_app.patch("/api/v1/backup_policies/{policy_id}", status_code=200)
def update_backup_policy(policy_id, item: backup_policy_update, identity: Json = Depends(auth.require_editor)):
    name = item.name
    description = item.description
    schedule = item.schedule
    retention = item.retention.model_dump() if item.retention else None
    storage = item.storage
    externalhook = item.externalhook
    enabled = item.enabled
    file_paths = checked_file_paths(item.file_paths)
    if name:
        check_name_is_free(name, policy_id)

    if schedule and not croniter.is_valid(schedule):
        raise HTTPException(
            status_code=400, detail='Provided crontab format is invalid')
    if enabled:
        if not type(enabled) == bool:
            raise HTTPException(
                status_code=400, detail='Provided enabled status is invalid (must be true/false)')
    return api_update_backup_policy(policy_id, name, description, schedule, retention, storage, externalhook, enabled,
                                    file_paths=file_paths)


@fastapi_app.delete("/api/v1/backup_policies/{policy_id}", status_code=200)
def delete_backup_policy(policy_id: str, identity: Json = Depends(auth.require_editor)):
    engine = database.init_db_connection()

    records = []
    with Session(engine) as session:
        statement = select(Pools).where(
            Pools.policy_id == ensure_uuid(policy_id))
        results = session.exec(statement)
        for policy in results:
            records.append(policy)
        if len(records) > 0:
            raise HTTPException(
                status_code=409, detail='One or more pools are linked to this policy.')
    return api_delete_backup_policy(policy_id)
