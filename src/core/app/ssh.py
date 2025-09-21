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


def __get_parent_directory() -> Path:
    return Path(get_env_var("SNAP_COMMON", allow_blank=True, allow_undefined=True) or "/root")


def __get_shared_directory() -> Path:
    return __get_parent_directory() / "shared_ssh"


def __get_local_directory() -> Path:
    return __get_parent_directory() / ".ssh"


def __get_sync_file() -> Path:
    return __get_shared_directory() / "sync"


def __get_private_key_paths() -> List[str]:
    return shell.subprocess_run(f"find '{__get_local_directory().as_posix()}' -name 'id_*' ! -name '*.pub'").splitlines()


@logged()
def manage_ssh_agent():
    env_var_names = ["SSH_AUTH_SOCK", "SSH_AGENT_PID"]
    def_separator = "="

    output = shell.subprocess_run(f"""
                         eval `ssh-agent`
                         ssh-add {" ".join(__get_private_key_paths())}
                         ssh-add -l
                         {"; ".join(map(lambda var_name: f"echo {var_name}{def_separator}${var_name}", env_var_names))}
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
def push_ssh_directory() -> None:
    __get_shared_directory().mkdir(parents=True, exist_ok=True)

    for key_type in ["rsa", "ed25519"]:
        key_path = __get_shared_directory() / f"id_{key_type}"
        if not key_path.exists():
            shell.subprocess_run(
                f'ssh-keygen -t {key_type} -b 2048 -N "" -C "$BACKROLL_HOST_USER@$BACKROLL_HOSTNAME(backroll)" -f "{key_path.as_posix()}" -q')

    config_path = __get_shared_directory() / "config"
    if not config_path.exists():
        # The file may be created before being written.
        # Thus, it is not suitable for synchronizing.
        with config_path.open("w") as config_file:
            config_file.write("""
                              Host *
                                StrictHostKeyChecking no
                              """)

    sync = __get_sync_file()
    if not sync.exists():
        sync.touch()


@logged()
def pull_ssh_directory(logger: Logger) -> None:
    __get_local_directory().mkdir(parents=True, exist_ok=True)

    while not __get_sync_file().exists():
        logger.info("Waiting for shared SSH directory…")
        sleep(1)

    src = __get_shared_directory().as_posix()
    dst = __get_local_directory().as_posix()

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

    manage_ssh_agent()


@dataclass
class SshPublicKey:
    name: str
    full_line: str


def list_public_keys() -> list[SshPublicKey]:
    return list(map(
        lambda path: SshPublicKey(
            Path(path).stem.removeprefix("id_"),
            # Removing simple quotes to prevent exiting from the sed script.
            # Pipes are the chosen delimiters for the sed address thus they are removed.
            shell.os_popen(f"cat {path}").strip()
                .replace("'", "").replace("|", "")),
        shell.os_popen(f"find {__get_local_directory().as_posix()}/*.pub").splitlines()))


class ConnectionException(Exception):
    def __init__(self, message):
        super().__init__(message)


def __get_ssh_private_keys() -> List[Tuple[str, str]]:
    private_key_paths = __get_private_key_paths()
    key_paths = []
    for path in private_key_paths:
        key_type = None
        if "id_rsa" in path:
            key_type = "RSA"
        elif "id_ed25519" in path:
            key_type = "ED25519"
        if key_type:
            key_paths.append((key_type, path))
    return key_paths


def connect_ssh(ip_address: str, username: str) -> Tuple[paramiko.SSHClient, Optional[Tuple[str, str]]]:
    """Establishes an SSH connection and returns the client and used key."""
    key_paths = __get_ssh_private_keys()
    if not key_paths:
        raise ConnectionException("No valid SSH private key found.")

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    connected = False
    used_key = None

    for key_type, path in key_paths:
        try:
            key = (
                paramiko.RSAKey.from_private_key_file(path)
                if key_type == "RSA"
                else paramiko.Ed25519Key.from_private_key_file(path)
            )
            logging.debug(
                f"Attempting connection with {key_type} key to {ip_address}")
            client.connect(hostname=ip_address, username=username, pkey=key)
            logging.info(
                f"SSH connection successful with {key_type} key to {ip_address}")
            connected = True
            used_key = (key_type, path)
            break
        except (paramiko.ssh_exception.AuthenticationException, paramiko.ssh_exception.SSHException) as e:
            logging.debug(f"Failed with {key_type} key: {e}")

    if not connected:
        client.close()
        raise ConnectionException("Unable to connect via SSH with any key.")

    return client, used_key


def init_ssh_connection(host_id, ip_address, username):
    try:
        shell.subprocess_run(f"""
                             ls -al {__get_local_directory().as_posix()}
                             eval `ssh-agent` && ssh-add -l
                             ssh {username}@{ip_address}""")
    except Exception as exception:
        print(exception)

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
            for public_key in list_public_keys():
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
