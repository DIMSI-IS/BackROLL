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

from dataclasses import dataclass
import logging
from logging import Logger
from pathlib import Path
from time import sleep
from typing import List, Tuple, Optional

import paramiko
import os
from sqlmodel import Session, select

from app import database
from app import shell
from app.logging import logged
from app.database import Hosts
from app.routes import host
from app.patch import ensure_uuid
from app.environment import get_env_var


def __get_source_directory() -> Path:
    return (Path(get_env_var("SNAP_COMMON", allow_blank=True, allow_undefined=True) or "/root") / "shared_ssh")


def __get_destination_directory() -> Path:
    return Path("/root/.ssh")


def __get_sync_file() -> Path:
    return __get_source_directory() / "sync"


def __get_private_key_paths() -> List[str]:
    return shell.subprocess_run(f"find '{__get_destination_directory().as_posix()}' -name 'id_*' ! -name '*.pub'").splitlines()


def __get_public_key_paths() -> List[str]:
    return shell.subprocess_run(f"find '{__get_destination_directory().as_posix()}' -name '*.pub'").splitlines()


@dataclass
class PrivateKey:
    type: str
    path: str


def __get_private_keys() -> List[PrivateKey]:
    return list(map(lambda path: PrivateKey(
        Path(path).stem.removeprefix("id_").upper(),
        path
    ), __get_private_key_paths()))


@dataclass
class PublicKey:
    name: str
    full_line: str


def get_public_keys() -> List[PublicKey]:
    return list(map(
        lambda path: PublicKey(
            Path(path).stem.removeprefix("id_"),
            # Removing simple quotes to prevent exiting from the sed script.
            # Pipes are the chosen delimiters for the sed address thus they are removed.
            shell.subprocess_run(f"cat {path}").strip()
                .replace("'", "").replace("|", "")),
        __get_public_key_paths()))


@logged()
def push_ssh_directory() -> None:
    __get_source_directory().mkdir(parents=True, exist_ok=True)

    for key_type in ["rsa", "ed25519"]:
        key_path = __get_source_directory() / f"id_{key_type}"
        if not key_path.exists():
            shell.subprocess_run(
                f'ssh-keygen -t {key_type} -b 2048 -N "" -C "$BACKROLL_HOST_USER@$BACKROLL_HOSTNAME(backroll)" -f "{key_path.as_posix()}" -q')

    # Must be copied to the /root/.ssh directory.
    config_path = __get_source_directory() / "config"
    if not config_path.exists():
        # The file may be created before being written.
        # Thus, it is not suitable for synchronizing.
        with config_path.open("w") as config_file:
            config_file.write("""
                              Host *
                                StrictHostKeyChecking no
                              """)

    # TODO Rename init ?
    sync = __get_sync_file()
    if not sync.exists():
        sync.touch()


@logged()
def __pull_ssh_directory(logger: Logger) -> None:
    __get_destination_directory().mkdir(parents=True, exist_ok=True)

    while not __get_sync_file().exists():
        logger.info("Waiting for shared SSH directory…")
        sleep(1)

    src = __get_source_directory().as_posix()
    dst = __get_destination_directory().as_posix()

    shell.subprocess_run(f"""
                         # Copy shared directory
                         cp {src}/* {dst}/
                         
                         # Ensure proper file permissions
                         
                         # From ssh-keygen behavior
                         chmod 600 {dst}/*
                         chmod 644 {dst}/*.pub

                         # From OpenSSH man pages
                         chmod 644 {dst}/config
                         """)


@logged()
def manage_ssh_agent():
    env_var_names = ["SSH_AUTH_SOCK", "SSH_AGENT_PID"]
    def_separator = "="

    output = shell.subprocess_run(f"""
                         eval `ssh-agent`
                         ssh-add {" ".join(__get_private_key_paths())}
                         ssh-add -l
                         {"; ".join(map(
                             lambda var_name: f"echo {var_name}{def_separator}${var_name}", env_var_names))}
                         """)

    for line in output.splitlines():
        if not def_separator in line:
            continue
        [name, value] = line.split(def_separator)
        if name in env_var_names:
            os.environ[name] = value

    # Check
    for var_name in env_var_names:
        get_env_var(var_name)


@logged()
def ensure_configuration():
    __pull_ssh_directory()
    manage_ssh_agent()


class ConnectionException(Exception):
    def __init__(self, message):
        super().__init__(message)


def connect_ssh(ip_address: str, username: str) -> Tuple[paramiko.SSHClient, Optional[PrivateKey]]:
    """Establishes an SSH connection and returns the client and used key."""
    private_keys = __get_private_keys()
    if not private_keys:
        raise ConnectionException("No valid SSH private key found.")

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    connected = False
    used_key = None

    # TODO try with SSH agent only.

    for pk in private_keys:
        try:
            key = (
                paramiko.RSAKey.from_private_key_file(pk.path)
                if pk.type == "RSA"
                else paramiko.Ed25519Key.from_private_key_file(pk.path)
            )
            logging.debug(
                f"Attempting connection with {pk.type} key to {ip_address}")
            client.connect(hostname=ip_address, username=username, pkey=key)
            logging.info(
                f"SSH connection successful with {pk.type} key to {ip_address}")
            connected = True
            used_key = pk
            break
        except (paramiko.ssh_exception.AuthenticationException, paramiko.ssh_exception.SSHException) as e:
            logging.debug(f"Failed with {pk.type} key: {e}")

    if not connected:
        client.close()
        raise ConnectionException("Unable to connect via SSH with any key.")

    return client, used_key


def init_ssh_connection(host_id, ip_address, username):
    logging.getLogger("paramiko").setLevel(logging.DEBUG)

    try:
        client, _ = connect_ssh(ip_address, username)
        try:
            host.filter_host_by_id(host_id)
            engine = database.init_db_connection()

            with Session(engine) as session:
                statement = select(Hosts).where(
                    Hosts.id == ensure_uuid(host_id))
                results = session.exec(statement)
                data_host = results.one()
                data_host.ssh = 1
                data_host.username = username
                session.add(data_host)
                session.commit()
                session.refresh(data_host)
        finally:
            client.close()

    except OSError:
        raise ConnectionException("The hypervisor is unreachable.")
    except paramiko.ssh_exception.AuthenticationException:
        raise ConnectionException(
            "Authentication to the hypervisor has failed.")


def remove_keys(ip_address, username):
    try:
        client, _ = connect_ssh(ip_address, username)
        try:
            for public_key in get_public_keys():
                _, _, stderr = client.exec_command(
                    f"sed -i '\\|{public_key.full_line}|d' ~/.ssh/authorized_keys"
                )
                error = stderr.read().decode()
                if error:
                    print(
                        f"[Warning] Removing {public_key.name} SSH public key from {ip_address} failed: {error}"
                    )
        finally:
            client.close()

    except OSError:
        raise ConnectionException("The hypervisor is unreachable.")
    except paramiko.ssh_exception.AuthenticationException:
        raise ConnectionException(
            "Authentication to the hypervisor has failed.")
