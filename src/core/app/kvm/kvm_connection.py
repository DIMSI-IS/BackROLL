# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

import os
import libvirt
from app.ssh import check_ssh_agent, get_local_directory, ConnectionException
from app import shell


def kvm_connection(hypervisor):
    """Establishes a libvirt connection to the remote host."""
    try:
        # Start SSH agent if not already running
        if not check_ssh_agent():
            result = shell.subprocess_run("ssh-agent -s")
            for line in result.splitlines():
                if line.startswith("SSH_AUTH_SOCK"):
                    key, value = line.split("=", 1)
                    os.environ[key] = value.split(";")[0]
                elif line.startswith("SSH_AGENT_PID"):
                    key, value = line.split("=", 1)
                    os.environ[key] = value.split(";")[0]

        # Add private keys to SSH agent
        local_ssh_dir = get_local_directory().as_posix()
        private_keys = shell.os_popen(
            f"find \"{local_ssh_dir}\" -type f -name 'id_*' ! -name '*.pub'"
        ).splitlines()
        if not private_keys:
            print(f"ERROR: No private keys found in {local_ssh_dir}")
            raise ConnectionException(
                f"No private keys found in {local_ssh_dir}")

        result = shell.subprocess_run(
            f"ssh-add $(find \"{local_ssh_dir}\" -type f -name 'id_*' ! -name '*.pub')"
        )

        # Verify loaded keys
        result = shell.subprocess_run("ssh-add -l")
        if not result.strip():
            print("ERROR: No SSH keys loaded in agent")
            raise ConnectionException("No SSH keys loaded in agent")

        # Test SSH connection
        username = hypervisor['username']
        ip_address = hypervisor['ipaddress']
        shell.subprocess_run(
            f"ssh -o StrictHostKeyChecking=no {username}@{ip_address} exit"
        )

        # Establish libvirt connection
        uri = f"qemu+ssh://{username}@{ip_address}/system"
        conn = libvirt.open(uri)
        return conn
    except libvirt.libvirtError as e:
        print(f"ERROR: Failed to connect to libvirt: {str(e)}")
        raise
    except Exception as e:
        print(f"ERROR: Failed to initialize libvirt connection: {str(e)}")
        raise ConnectionException(
            f"Failed to initialize libvirt connection: {str(e)}")
    finally:
        # Clean up SSH agent if started
        if "SSH_AGENT_PID" in os.environ:
            try:
                pid = os.environ['SSH_AGENT_PID']
                shell.subprocess_run(f"kill {pid}")
            except shell.ShellException as e:
                print(f"WARNING: Failed to terminate SSH agent: {e.stderr}")
