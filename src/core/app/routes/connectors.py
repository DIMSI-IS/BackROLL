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
from fastapi import HTTPException, Depends
from pydantic import Json
from sqlmodel import Session, select
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Json
from pathlib import Path

import base64
from cryptography.fernet import Fernet

from app import app
from app import celery

from app import auth
from app import database

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

def encrypt_password(password):
  if not Path('./secret.key').is_file():
    # Adding the salt to password
    key = Fernet.generate_key()
    file = open('./secret.key', 'wb+')
    file.write(key)
  else:
    key = Path('./secret.key').read_text()

  # Encrypt a message
  fernet = Fernet(key)
  return fernet.encrypt(password.encode())

@celery.task(name='create connector')
def api_create_connector(name, url, login, password):
  try:
    engine = database.init_db_connection()
  except Exception as e:
    raise ValueError(e)
  try:
    new_connector = Connectors(name=name, url=url, login=login, password=password)
    with Session(engine) as session:
        session.add(new_connector)
        session.commit()
        session.refresh(new_connector)
    return new_connector
  except Exception as e:
    raise ValueError(e)

@celery.task(name='list connectors')
def api_retrieve_connectors():
  try:
    engine = database.init_db_connection()
  except Exception as e:
    raise ValueError(e)
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

@app.post('/api/v1/connectors', status_code=201)
def create_connector(item: items_create_connector, identity: Json = Depends(auth.valid_token)):
  name = item.name
  url = item.url
  login = base64.b64encode(encrypt_password(item.login))
  password = base64.b64encode(encrypt_password(item.password))
  return api_create_connector(name, url, login, password)

@app.get('/api/v1/connectors', status_code=202)
def retrieve_connectors(identity: Json = Depends(auth.valid_token)):
  task = api_retrieve_connectors.delay()
  return {'Location': app.url_path_for('retrieve_task_status', task_id=task.id)}


# @app.delete('/api/v1/virtualmachines/{virtual_machine_id}/backups/{backup_name}', status_code=202)
# def delete_specific_virtual_machine_backup(virtual_machine_id, backup_name, identity: Json = Depends(auth.valid_token)):
#   if not virtual_machine_id: raise HTTPException(status_code=404, detail='Virtual machine not found')
#   if not backup_name: raise HTTPException(status_code=404, detail='Backup not found')
#   res = chain(host.retrieve_host.s(), dmap.s(parse_host.s()), handle_results.s(), manage_backup.remove_archive.s(virtual_machine_id, backup_name)).apply_async() 
#   return {'Location': app.url_path_for('retrieve_task_status', task_id=res.id)}

# @app.get('/api/v1/virtualmachines/{virtual_machine_id}/repository', status_code=202)
# def list_virtual_machine_repository(virtual_machine_id, identity: Json = Depends(auth.valid_token)):
#   if not virtual_machine_id: raise HTTPException(status_code=404, detail='Virtual machine not found')
#   res = chain(host.retrieve_host.s(), dmap.s(parse_host.s()), handle_results.s(), retrieve_virtual_machine_repository.s(virtual_machine_id)).apply_async() 
#   return {'Location': app.url_path_for('retrieve_task_status', task_id=res.id)}