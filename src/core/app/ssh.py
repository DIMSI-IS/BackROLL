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
from logging import Logger
from pathlib import Path
from time import sleep

import paramiko
from sqlmodel import Session, select

from app import database
from app import shell
from app.logging import logged
from app.database import Hosts
from app.routes import host
from app.patch import make_path, ensure_uuid


# def __get_ssh_directory() -> str:
#     return "/root/.ssh"

# @logged()
#  def ensure_set_keys() -> None:
#     for key_type in ["rsa", "ed25519"]:
#         key_file = make_path("/root/shared_ssh", f"id_{key_type}")
#         if not Path(key_file).exists():
#             shell.subprocess_run(
#                 f'ssh-keygen -t {key_type} -b 2048 -N "" -C "$BACKROLL_HOST_USER@$BACKROLL_HOSTNAME(backroll)" -f "{key_file}" -q')


@logged()
def get_keys(logger: Logger) -> None:
    source = "/root/shared_ssh/id_rsa"

    while not Path(source).exists():
        logger.info("Waiting for keys…")
        sleep(1)

    shell.subprocess_run(f"""
cp /root/shared_ssh/* /root/.ssh/

# Ensure proper file permissions

# From ssh-keygen behavior
chmod 600 /root/.ssh/*
chmod 644 /root/.ssh/*.pub

# From OpenSSH man pages
chmod 644 /root/.ssh/config
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
        shell.os_popen('find /root/.ssh/*.pub').splitlines()))


class ConnectionException(Exception):
    def __init__(self, message):
        super().__init__(message)


def init_ssh_connection(host_id, ip_address, username):
    shell.subprocess_run(f"ls -al /root/.ssh")

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
