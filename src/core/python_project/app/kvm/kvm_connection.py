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
from app.ssh import manage_ssh_agent, ConnectionException
from app import shell


def kvm_connection(hypervisor):
    """Establishes a libvirt connection to the remote host."""
    try:
        manage_ssh_agent()

        username = hypervisor['username']
        ip_address = hypervisor['ipaddress']

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
