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

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select
from fastapi.encoders import jsonable_encoder

from app.kvm import kvm_connection
from app import database
from app.database import Hosts

def check_kvm(host):
  try:
    engine = database.init_db_connection()
  except Exception as e:
    raise HTTPException(status_code=500, detail=jsonable_encoder(e))

  with Session(engine) as session:
    statement = select(Hosts).where(Hosts.id == host.id)
    results = session.exec(statement)
    selectedHost = results.one()
    connection_state = None
    # Setting up network connection
    conn = kvm_connection.kvm_connection(host)
    # If KVM connection is up
    if conn != None:
      selectedHost.ssh = 1
    # If KVM connection is down
    else:
      selectedHost.ssh = 0
    session.add(selectedHost)
    session.commit()
    session.refresh(selectedHost)      
    connection_state = True
  return connection_state