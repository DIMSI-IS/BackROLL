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

import paramiko
import os
from sqlmodel import Session, select

from app import database
from app import shell
from app.logging import logged
from app.database import Hosts
from app.routes import host
from app.patch import ensure_uuid


def __get_shared_ssh_directory() -> Path:
    snap_common = os.getenv("SNAP_COMMON")

    if snap_common:
        return Path(snap_common) / ".ssh" / "shared_ssh"

    raise RuntimeError(
        "SNAP_COMMON is not set! "
        "Cannot continue safely. Check your Snap environment."
    )


def __get_sync_file() -> Path:
    return __get_shared_ssh_directory() / "sync"


def __get_local_ssh_directory() -> Path:
    return Path("/var/snap/backroll/common/.ssh/local_ssh")


@logged()
def push_ssh_directory() -> None:
    
    __get_shared_ssh_directory().mkdir(parents=True, exist_ok=True)

    for key_type in ["rsa", "ed25519"]:
        key_path = __get_shared_ssh_directory() / f"id_{key_type}"
        if not key_path.exists():
            shell.subprocess_run(
                f'ssh-keygen -t {key_type} -b 2048 -N "" -C "$BACKROLL_HOST_USER@$BACKROLL_HOSTNAME(backroll)" -f "{key_path.as_posix()}" -q')

    config_path = __get_shared_ssh_directory() / "config"
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
    while not __get_sync_file().exists():
        logger.info("Waiting for shared SSH directory…")
        sleep(1)

    src = __get_shared_ssh_directory().as_posix()
    dst = __get_local_ssh_directory().as_posix()

    __get_local_ssh_directory().mkdir(parents=True, exist_ok=True)

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

    # TODO Test if it is useful.
    shell.subprocess_run(f"""
                         eval `ssh-agent`
                         ssh-add $(find "{dst}" | grep -E "id_[^.]+$")
                         """)


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
        shell.os_popen(f"find {__get_local_ssh_directory().as_posix()}/*.pub").splitlines()))


class ConnectionException(Exception):
    def __init__(self, message):
        super().__init__(message)


def init_ssh_connection(host_id, ip_address, username):
    try:
        shell.subprocess_run(f"""
                             ls -al {__get_local_ssh_directory().as_posix()}
                             eval `ssh-agent` && ssh-add -l
                             ssh {username}@{ip_address}""")
    except Exception as exception:
        print(exception)

    logging.getLogger("paramiko").setLevel(logging.DEBUG)

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(
            hostname=ip_address,
            username=username,
        )
        client.close()
    except OSError:
        raise ConnectionException(
            "The hypervisor is unreachable.")
    except paramiko.ssh_exception.AuthenticationException:
        raise ConnectionException(
            "Authentication to the hypervisor has failed.")

    host.filter_host_by_id(host_id)
    engine = database.init_db_connection()

    with Session(engine) as session:
        statement = select(Hosts).where(Hosts.id == ensure_uuid(host_id))
        results = session.exec(statement)
        data_host = results.one()
        data_host.ssh = 1
        data_host.username = username
        session.add(data_host)
        session.commit()
        session.refresh(data_host)


def remove_key(ip_address, username):
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=ip_address,
            username=username,
        )
        for public_key in list_public_keys():
            # The sed script is delimited with simple quotes to prevent shell parameter expansion.
            # Slashes are used to encode the key in base64 so the sed address is delimeted with pipes.
            _, _, stderr = client.exec_command(
                f"sed -i '\\|{public_key.full_line}|d' ~/.ssh/authorized_keys")
            error = stderr.read().decode()
            if error:
                print(
                    f"[Warning] Removing {public_key.name} SSH public key from {ip_address} failed: {error}")
        client.close()
    except Exception as e:
        raise ValueError(e)
