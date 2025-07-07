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

from pathlib import Path
from urllib.parse import quote_plus
import uuid
from uuid import UUID
from typing import Optional
from sqlmodel import Field, SQLModel, create_engine

from app.environment import get_env_var


class Policies(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid.uuid4,
                     primary_key=True, nullable=False)
    name: str
    description: str
    schedule: str
    retention_day: int
    retention_week: int
    retention_month: int
    retention_year: int
    storage: Optional[UUID] = Field(default=None, foreign_key="storage.id")
    externalhook: Optional[UUID] = Field(
        default=None, foreign_key="externalhooks.id")
    enabled: Optional[bool] = 0


class Pools(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid.uuid4,
                     primary_key=True, nullable=False)
    name: Optional[str] = None
    policy_id: Optional[UUID] = Field(default=None, foreign_key="policies.id")
    connector_id: Optional[UUID] = Field(
        default=None, foreign_key="connectors.id")

    def to_json(self):
        return {
            "id": str(self.id),
            "name": self.name,
            "policy_id": str(self.policy_id),
            "connector_id": str(self.connector_id),
        }


class Hosts(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid.uuid4,
                     primary_key=True, nullable=False)
    hostname: str
    ipaddress: str
    username: Optional[str] = None
    ssh: Optional[bool] = 0
    pool_id: Optional[UUID] = Field(default=None, foreign_key="pools.id")
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
    id: UUID = Field(default_factory=uuid.uuid4,
                     primary_key=True, nullable=False)
    name: str
    path: str

    def to_json(self):
        return {
            "id": str(self.id),
            "name": self.name,
            "path": self.path,
        }


class ExternalHooks(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid.uuid4,
                     primary_key=True, nullable=False)
    name: str
    value: str


class Connectors(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid.uuid4,
                     primary_key=True, nullable=False)
    name: str
    url: str
    login: str
    password: str


class User(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid.uuid4,
                     primary_key=True, nullable=False)
    # TODO Choose username length
    name: str  # = Field(sa_column=Column("name", VARCHAR, unique=True))
    password_hash: bytes


def __get_db_url():
    try:
        # TODO Rename IP to address ?
        return f"mysql+mysqlconnector://{get_env_var("DB_USER_NAME")}:{quote_plus(get_env_var("DB_USER_PASSWORD"))}@{get_env_var("DB_IP")}:{get_env_var("DB_PORT")}/{get_env_var("DB_BASE")}"
    except:
        # TODO Debug log ?
        pass

    try:
        return f"sqlite:///{Path(get_env_var("SNAP_COMMON"), "database.sqlite")}"
    except:
        # TODO Debug log ?
        pass

    return f"sqlite:////var/lib/backroll/database.sqlite"


def init_db_connection():
    return create_engine(__get_db_url())
