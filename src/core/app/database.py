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
import sys
from urllib.parse import quote_plus
import uuid as uuid_pkg
from typing import Optional
from sqlmodel import Field, SQLModel, create_engine

# Other imports
import os
import json
from app import app
from app import celery as celeryWorker
from app import celery

class Policies(SQLModel, table=True):
  id: uuid_pkg.UUID = Field(default_factory=uuid_pkg.uuid4, primary_key=True, nullable=False)
  name: str
  description: str
  schedule: str
  retention_day: int
  retention_week: int
  retention_month: int
  retention_year: int
  storage: uuid_pkg.UUID = Field(default=None, foreign_key="storage.id")
  externalhook: uuid_pkg.UUID = Field(default=None, foreign_key="externalhooks.id")
  enabled: Optional[bool] = 0

class Pools(SQLModel, table=True):
  id: uuid_pkg.UUID = Field(default_factory=uuid_pkg.uuid4, primary_key=True, nullable=False)
  name: Optional[str] = None
  policy_id: uuid_pkg.UUID = Field(default=None, foreign_key="policies.id")
  connector_id: uuid_pkg.UUID = Field(default=None, foreign_key="connectors.id")
  def to_json(self):
    return {
      "id": str(self.id),
      "name": self.name,
      "policy_id": str(self.policy_id),
      "ssh": bool(self.is_managed),
    }

class Hosts(SQLModel, table=True):
  id: uuid_pkg.UUID = Field(default_factory=uuid_pkg.uuid4, primary_key=True, nullable=False)
  hostname: str
  ipaddress: str
  username: Optional[str] = None
  ssh: Optional[bool] = 0
  pool_id: uuid_pkg.UUID = Field(default=None, foreign_key="pools.id")
  tags: Optional[str] = None
  state: Optional[bool] = 0

  def to_json(self):
    return {
      "id": str(self.id),
      "hostname": self.hostname,
      "ipaddress": self.ipaddress,
      "username": self.username,
      "ssh": bool(self.ssh),
      "pool_id": str(self.pool_id),
      "tags": self.tags,
      "state": bool(self.state)
    }

class Storage(SQLModel, table=True):
  id: uuid_pkg.UUID = Field(default_factory=uuid_pkg.uuid4, primary_key=True, nullable=False)
  name: str
  path: str
  def to_json(self):
    return {
      "id": str(self.id),
      "name": self.name,
      "path": self.path,
    }

class ExternalHooks(SQLModel, table=True):
  id: uuid_pkg.UUID = Field(default_factory=uuid_pkg.uuid4, primary_key=True, nullable=False)
  name: str
  value: str

class Connectors(SQLModel, table=True):
  id: uuid_pkg.UUID = Field(default_factory=uuid_pkg.uuid4, primary_key=True, nullable=False)
  name: str
  url: str
  login: str
  password: str

@app.on_event("startup")
async def startup_event():
  # If DB is not yet configured, proceed to initialization
  engine = init_db_connection()
  SQLModel.metadata.create_all(engine)

  # Add default connectors
  


def init_db_connection():
  if not 'DB_USER_NAME' in os.environ:
    sys.exit("Missing required environment variable: DB_USER_NAME. Check your backroll_config.yml file")

  if not 'DB_USER_PASSWORD' in os.environ:
    sys.exit("Missing required environment variable: DB_USER_PASSWORD. Check your backroll_config.yml file")

  if not 'DB_IP' in os.environ:
    sys.exit("Missing required environment variable: DB_IP. Check your backroll_config.yml file")

  if not 'DB_PORT' in os.environ:
    sys.exit("Missing required environment variable: DB_PORT. Check your backroll_config.yml file")

  if not 'DB_BASE' in os.environ:
    sys.exit("Missing required environment variable: DB_BASE. Check your backroll_config.yml file")
  try:
    mysql_url = f'''mysql+mysqlconnector://{os.getenv("DB_USER_NAME")}:%s@{os.getenv("DB_IP")}:{os.getenv("DB_PORT")}/{os.getenv("DB_BASE")}'''
    return create_engine(mysql_url % quote_plus(os.getenv("DB_USER_PASSWORD")))
  except Exception as e:
    sys.exit(e)
