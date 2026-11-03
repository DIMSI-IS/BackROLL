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

import json
from datetime import datetime, timezone
from logging import Logger
from pathlib import Path
from urllib.parse import quote_plus
import uuid
from uuid import UUID
from typing import Optional
import sqlalchemy
from sqlalchemy import Column, Float, Text
from sqlmodel import Field, SQLModel, create_engine

from app.environment import MissingEnvironmentVariableException, get_env_var
from app.logging import logged


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
    # Folders and files of the virtual machines to back up too, one path per line.
    file_paths: Optional[str] = None


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
    # The address of the webhook, encrypted (app/vault.py): longer than a plain address.
    value: str = Field(sa_column=Column(Text, nullable=False))


class Connectors(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid.uuid4,
                     primary_key=True, nullable=False)
    name: str
    url: str
    login: str
    # The secret key of the API, encrypted (app/vault.py): longer than a plain key.
    password: str = Field(sa_column=Column(Text, nullable=False))


class User(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid.uuid4,
                     primary_key=True, nullable=False)
    name: str = Field(max_length=64, unique=True, index=True)
    password_hash: bytes
    # One of app.auth.roles.Role values.
    role: str = Field(default="viewer", max_length=16)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc))
    # Failed logins since the last success or lock, and the end of the lock.
    failed_attempts: int = Field(default=0)
    locked_until: Optional[datetime] = None
    # "local": the password is checked by BackROLL. "ad": the user comes from the Active Directory, which checks
    # the password, and whose groups give the role (see app/auth/directory.py).
    auth_source: str = Field(default="local", max_length=16)
    external_dn: Optional[str] = Field(default=None, max_length=512)
    display_name: Optional[str] = Field(default=None, max_length=256)
    email: Optional[str] = Field(default=None, max_length=256)
    last_login_at: Optional[datetime] = None

    def is_locked(self) -> bool:
        if self.locked_until is None:
            return False
        locked_until = self.locked_until
        if locked_until.tzinfo is None:
            # The database returns naive datetimes, which are UTC.
            locked_until = locked_until.replace(tzinfo=timezone.utc)
        return locked_until > datetime.now(timezone.utc)

    def _utc_created_at(self):
        # The database returns naive datetimes, which are UTC.
        if not self.created_at:
            return None
        created_at = self.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        return created_at.isoformat()

    def to_json(self):
        return {
            "id": str(self.id),
            "name": self.name,
            "role": self.role,
            "is_active": bool(self.is_active),
            "locked": self.is_locked(),
            "created_at": self._utc_created_at(),
            "auth_source": self.auth_source or "local",
            "display_name": self.display_name,
            "email": self.email,
            "last_login_at": (self.last_login_at.replace(tzinfo=timezone.utc).isoformat()
                              if self.last_login_at else None),
        }


class DirectoryConfig(SQLModel, table=True):
    """The Active Directory that authenticates users. A single row (id 1)."""
    id: int = Field(default=1, primary_key=True)
    enabled: bool = Field(default=False)
    # ldaps://dc01.example.com:636 (or ldap:// with start_tls).
    server_url: str = Field(default="", max_length=512)
    start_tls: bool = Field(default=False)
    verify_certificate: bool = Field(default=True)
    # PEM of the certification authority of the directory, when it is not in the system store.
    ca_certificate: Optional[str] = Field(default=None, sa_column=Column(Text))
    base_dn: str = Field(default="", max_length=512)
    # The account that looks for users and groups: read only is enough.
    bind_dn: str = Field(default="", max_length=512)
    bind_password: str = Field(default="", max_length=512)
    # {username} is replaced by what the user typed, escaped.
    user_filter: str = Field(
        default="(&(objectCategory=person)(objectClass=user)(|(sAMAccountName={username})(userPrincipalName={username})))",
        max_length=1024)
    # A user is also in the groups that contain his groups.
    nested_groups: bool = Field(default=True)
    timeout_seconds: int = Field(default=10)


class DirectoryGroup(SQLModel, table=True):
    """What the members of a group of the directory can do in BackROLL."""
    id: UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)
    group_dn: str = Field(max_length=512, unique=True, index=True)
    name: str = Field(max_length=256)
    # One of app.auth.roles.Role values.
    role: str = Field(max_length=16)


class Setting(SQLModel, table=True):
    """A setting of the application that an administrator changes in the interface."""
    key: str = Field(primary_key=True, max_length=64)
    value: str = Field(max_length=256)


class DiskBackupState(SQLModel, table=True):
    """Where each disk of a machine is in its backup, written at each step.

    A step "NEEDS_ATTENTION" means that the disk may not be in the state a backup needs (for example the machine
    writes in an overlay file): the next backups of the machine are refused until an administrator clears it."""
    vm_uuid: str = Field(primary_key=True, max_length=64)
    disk: str = Field(primary_key=True, max_length=64)
    vm_name: str = Field(max_length=255)
    step: str = Field(max_length=32)
    message: Optional[str] = Field(default=None, sa_column=Column(Text))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # When the attention was asked, to show for how long a machine waits.
    attention_since: Optional[datetime] = None


class StorageCleanup(SQLModel, table=True):
    """How the old backups of a backup storage are cleaned."""
    storage_id: UUID = Field(primary_key=True, foreign_key="storage.id")
    # One backup per day is kept for this number of days, the older ones are deleted.
    keep_days: int = 30
    # Clean the repository of a machine right after its backup.
    after_backup: bool = False
    # Clean all the repositories of the storage on a schedule (cron, 5 fields).
    scheduled: bool = False
    schedule: str = Field(default="0 4 * * 0", max_length=64)
    # The external hook that is told when a cleaning starts and ends.
    hook_id: Optional[UUID] = Field(default=None, foreign_key="externalhooks.id")


class CleanupRun(SQLModel, table=True):
    """One cleaning: what was deleted, and its log."""
    id: UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)
    storage_id: UUID = Field(index=True)
    storage_name: str = Field(max_length=255)
    # "prune" (old backups) or "orphans" (repositories of machines that no longer exist).
    kind: str = Field(max_length=16)
    # "manual", "scheduled" or "after_backup".
    trigger: str = Field(max_length=16)
    user: Optional[str] = Field(default=None, max_length=64)
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
    finished_at: Optional[datetime] = None
    status: str = Field(default="running", max_length=16)
    summary: Optional[str] = Field(default=None, sa_column=Column(Text))
    log: Optional[str] = Field(default=None, sa_column=Column(Text))


class TaskRun(SQLModel, table=True):
    """A backup or a restore, kept after Flower forgets it. Times are in seconds since 1970."""
    id: str = Field(primary_key=True, max_length=64)
    name: str = Field(max_length=64, index=True)
    state: str = Field(default="STARTED", max_length=16)
    # Double precision: MariaDB keeps only 7 digits in a FLOAT, which rounds a time of 1792353940 to 1792350000.
    started: float = Field(sa_column=Column(Float(53), index=True, nullable=False))
    finished: Optional[float] = Field(default=None, sa_column=Column(Float(53), nullable=True))
    args: Optional[str] = Field(default=None, sa_column=Column(Text))
    error: Optional[str] = Field(default=None, sa_column=Column(Text))


class AuditLog(SQLModel, table=True):
    """Who did what. User names are copied, so entries outlive the deleted users."""
    id: UUID = Field(default_factory=uuid.uuid4,
                     primary_key=True, nullable=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), index=True)
    user_id: Optional[UUID] = None
    username: Optional[str] = Field(default=None, max_length=64, index=True)
    action: str = Field(max_length=128)
    method: str = Field(max_length=8)
    path: str = Field(max_length=512)
    status_code: int
    ip_address: Optional[str] = Field(default=None, max_length=64)
    detail: Optional[str] = Field(default=None, max_length=1024)
    # Where the user was authenticated: "local" or "ad" (Active Directory).
    source: str = Field(default="local", max_length=16)

    def to_json(self):
        created_at = self.created_at
        if created_at.tzinfo is None:
            # The database returns naive datetimes, which are UTC.
            created_at = created_at.replace(tzinfo=timezone.utc)
        return {
            "id": str(self.id),
            "source": self.source or "local",
            "created_at": created_at.isoformat(),
            "user_id": str(self.user_id) if self.user_id else None,
            "username": self.username,
            "action": self.action,
            "method": self.method,
            "path": self.path,
            "status_code": self.status_code,
            "ip_address": self.ip_address,
            "detail": self.detail,
        }


class DrpRun(SQLModel, table=True):
    """One disaster recovery restore. Names are copied, so entries outlive what they refer to."""
    id: UUID = Field(default_factory=uuid.uuid4,
                     primary_key=True, nullable=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), index=True)
    finished_at: Optional[datetime] = None
    user_id: Optional[UUID] = None
    username: Optional[str] = Field(default=None, max_length=64)
    repository: str = Field(max_length=128)
    # JSON list of the backup archives restored.
    disks: str = Field(max_length=1024)
    connector_id: Optional[UUID] = None
    connector_name: Optional[str] = Field(default=None, max_length=128)
    domain_id: Optional[str] = Field(default=None, max_length=64)
    domain_name: Optional[str] = Field(default=None, max_length=255)
    account: Optional[str] = Field(default=None, max_length=100)
    vm_name: str = Field(max_length=63)
    vm_id: Optional[str] = Field(default=None, max_length=64)
    # queued, running, success or failed.
    status: str = Field(default="queued", max_length=16, index=True)
    step: Optional[str] = Field(default=None, max_length=256)
    log: Optional[str] = Field(default=None, sa_column=sqlalchemy.Column(sqlalchemy.Text))
    error: Optional[str] = Field(default=None, sa_column=sqlalchemy.Column(sqlalchemy.Text))
    task_id: Optional[str] = Field(default=None, max_length=64)

    def to_json(self, with_log: bool = False):
        def utc(value):
            if value is None:
                return None
            # The database returns naive datetimes, which are UTC.
            return (value if value.tzinfo else value.replace(tzinfo=timezone.utc)).isoformat()

        data = {
            "id": str(self.id),
            "created_at": utc(self.created_at),
            "finished_at": utc(self.finished_at),
            "username": self.username,
            "repository": self.repository,
            "disks": json.loads(self.disks),
            "connector_name": self.connector_name,
            "domain_id": self.domain_id,
            "domain_name": self.domain_name,
            "account": self.account,
            "vm_name": self.vm_name,
            "vm_id": self.vm_id,
            "status": self.status,
            "step": self.step,
            "error": self.error,
        }
        if with_log:
            data["log"] = self.log
        return data


@logged()
def __get_db_url(logger: Logger):
    # Explicit choice of an SQLite file, used by the tests so that they never touch a real database.
    sqlite_directory = get_env_var("SQLITE_DIRECTORY", allow_undefined=True)
    if sqlite_directory:
        directory = Path(sqlite_directory)
        directory.mkdir(parents=True, exist_ok=True)
        logger.info("Using the SQLite file of SQLITE_DIRECTORY.")
        return f"sqlite:///{directory / "database.sqlite"}"

    try:
        url = f"mysql+mysqlconnector://{get_env_var("DB_USER_NAME")}:{quote_plus(get_env_var("DB_USER_PASSWORD"))}@{get_env_var("DB_ADDRESS")}:{get_env_var("DB_PORT")}/{get_env_var("DB_BASE")}"
        logger.info("Database settings found.")
        return url
    except MissingEnvironmentVariableException as exception:
        logger.info(f"No database settings. {exception}")

    logger.info("Using the default database file.")
    directory = Path("/var/lib/backroll")
    directory.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{directory / "database.sqlite"}"


__DB_URL = __get_db_url()


def init_db_connection():
    return create_engine(__DB_URL)


@logged()
def migrate_user_table(engine, logger: Logger):
    """Add the access control columns to a user table created before roles existed.

    `SQLModel.metadata.create_all` never alters existing tables.
    Users created before roles had full access, so they become admins.
    """
    inspector = sqlalchemy.inspect(engine)
    if "user" not in inspector.get_table_names():
        return

    table = engine.dialect.identifier_preparer.quote("user")
    columns = {column["name"] for column in inspector.get_columns("user")}
    statements = {
        "role": f"ALTER TABLE {table} ADD COLUMN role VARCHAR(16) NOT NULL DEFAULT 'admin'",
        "is_active": f"ALTER TABLE {table} ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1",
        "created_at": f"ALTER TABLE {table} ADD COLUMN created_at DATETIME NULL",
        "failed_attempts": f"ALTER TABLE {table} ADD COLUMN failed_attempts INT NOT NULL DEFAULT 0",
        "locked_until": f"ALTER TABLE {table} ADD COLUMN locked_until DATETIME NULL",
        "auth_source": f"ALTER TABLE {table} ADD COLUMN auth_source VARCHAR(16) NOT NULL DEFAULT 'local'",
        "external_dn": f"ALTER TABLE {table} ADD COLUMN external_dn VARCHAR(512) NULL",
        "display_name": f"ALTER TABLE {table} ADD COLUMN display_name VARCHAR(256) NULL",
        "email": f"ALTER TABLE {table} ADD COLUMN email VARCHAR(256) NULL",
        "last_login_at": f"ALTER TABLE {table} ADD COLUMN last_login_at DATETIME NULL",
    }
    with engine.begin() as connection:
        for column, statement in statements.items():
            if column not in columns:
                logger.info(f"Adding column “{column}” to the user table.")
                connection.execute(sqlalchemy.text(statement))

    indexed = {tuple(index["column_names"]) for index in inspector.get_indexes("user")}
    if ("name",) not in indexed:
        try:
            with engine.begin() as connection:
                connection.execute(sqlalchemy.text(
                    f"CREATE UNIQUE INDEX ix_user_name ON {table} (name)"))
        except sqlalchemy.exc.DatabaseError as exception:
            logger.warning(f"Could not make user names unique. {exception}")


@logged()
def migrate_policy_table(engine, logger: Logger):
    """Add the file_paths column to a policies table created before the backup of folders."""
    inspector = sqlalchemy.inspect(engine)
    if "policies" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("policies")}
    if "file_paths" not in columns:
        logger.info("Adding column “file_paths” to the policies table.")
        with engine.begin() as connection:
            connection.execute(sqlalchemy.text("ALTER TABLE policies ADD COLUMN file_paths TEXT NULL"))


@logged()
def migrate_task_run_table(engine, logger: Logger):
    """The times of the history of the tasks were created as FLOAT, which MariaDB rounds to 7 digits."""
    if engine.dialect.name not in ("mysql", "mariadb"):
        return
    inspector = sqlalchemy.inspect(engine)
    if "taskrun" not in inspector.get_table_names():
        return
    columns = {column["name"]: str(column["type"]).upper() for column in inspector.get_columns("taskrun")}
    statements = {"started": "ALTER TABLE taskrun MODIFY COLUMN started DOUBLE NOT NULL",
                  "finished": "ALTER TABLE taskrun MODIFY COLUMN finished DOUBLE NULL"}
    with engine.begin() as connection:
        for column, statement in statements.items():
            if "DOUBLE" not in columns.get(column, "DOUBLE"):
                logger.info(f"Changing the column “{column}” of the task history to double precision.")
                connection.execute(sqlalchemy.text(statement))


@logged()
def migrate_audit_table(engine, logger: Logger):
    """The audit log of a version without Active Directory has no column for the source of the user."""
    inspector = sqlalchemy.inspect(engine)
    if "auditlog" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("auditlog")}
    if "source" not in columns:
        logger.info("Adding the column “source” to the audit log.")
        with engine.begin() as connection:
            connection.execute(sqlalchemy.text(
                "ALTER TABLE auditlog ADD COLUMN source VARCHAR(16) NOT NULL DEFAULT 'local'"))


@logged()
def migrate_secrets(engine, logger: Logger):
    """Encrypt the secrets stored in clear by a version without encryption: the secret key of the connectors and the
    address of the webhooks. An encrypted value is longer than a plain one, so MariaDB columns of 255 characters grow.

    Without a key (SECRETS_KEY or JWT_SECRET) nothing is changed: the values are still read as they are.
    """
    from app import vault

    tables = {"connectors": "password", "externalhooks": "value"}
    inspector = sqlalchemy.inspect(engine)
    for table, column in tables.items():
        if table not in inspector.get_table_names():
            continue
        if engine.dialect.name in ("mysql", "mariadb"):
            current = {item["name"]: str(item["type"]).upper() for item in inspector.get_columns(table)}
            if "TEXT" not in current.get(column, "TEXT"):
                logger.info(f"Changing the column “{column}” of {table} to TEXT, to hold the encrypted value.")
                with engine.begin() as connection:
                    connection.execute(sqlalchemy.text(f"ALTER TABLE {table} MODIFY COLUMN {column} TEXT NOT NULL"))
        with engine.begin() as connection:
            rows = connection.execute(sqlalchemy.text(f"SELECT id, {column} FROM {table}")).all()
            for identifier, value in rows:
                if not value or vault.is_encrypted(value):
                    continue
                try:
                    encrypted = vault.encrypt(value)
                except vault.SecretError as exception:
                    logger.warning(f"The secrets of {table} stay in clear. {exception}")
                    return
                connection.execute(sqlalchemy.text(f"UPDATE {table} SET {column} = :value WHERE id = :id"),
                                   {"value": encrypted, "id": identifier})
                logger.info(f"A secret of {table} has been encrypted.")
