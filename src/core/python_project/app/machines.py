"""The names of all the virtual machines that exist, for the cleaning of the backups of deleted machines.

The lists of the Virtual machines page are made to be shown: a hypervisor that does not answer, or an
error of CloudStack, gives an empty list without a word. Here an empty answer must never be taken for
"the machines are gone": every doubt is returned as a warning, and the cleaning then refuses to decide.
"""

import shlex

from fastapi.encoders import jsonable_encoder
from sqlmodel import Session, select

from app import shell
from app.auth.password import get_engine
from app.cloudstack import endpoint
from app.database import Connectors, Hosts, Pools

# The machines of the projects of CloudStack are only listed with this value.
ALL_PROJECTS = "-1"


def list_kvm_names(host: Hosts) -> set[str]:
    if not host.ssh:
        raise RuntimeError("not connected to BackROLL (SSH): its machines cannot be listed")
    last_error = None
    for _ in range(2):
        try:
            shell.os_system(f"nc -z -w 3 {shlex.quote(host.ipaddress)} 22 > /dev/null")
            last_error = None
            break
        except shell.ShellException:
            last_error = "unreachable"
    if last_error:
        raise RuntimeError("unreachable")
    # Imported here: the modules of the hypervisors import each other, and the order matters.
    from app.kvm import kvm_manage_vm
    machines = kvm_manage_vm.retrieve_virtualmachine(jsonable_encoder(host))
    return {machine["name"] for machine in machines}


def list_cloudstack_names(connector: Connectors) -> set[str]:
    """Every machine of the account, with all the pages, and the machines of the projects.
    Any error is raised: nothing is swallowed."""
    cs = endpoint.cloudstack_connector(connector)
    names: set[str] = set()
    for extra in ({}, {"projectid": ALL_PROJECTS}):
        for machine in cs.listVirtualMachines(listall=True, fetch_list=True, **extra):
            names.add(machine["instancename"])
    return names


def list_machine_names() -> tuple[set[str], list[str]]:
    """(the names, the reasons why the list may be incomplete)."""
    names: set[str] = set()
    warnings: list[str] = []
    with Session(get_engine()) as session:
        hosts = session.exec(select(Hosts)).all()
        pools = session.exec(select(Pools)).all()
        connectors = {}
        for pool in pools:
            if pool.connector_id and pool.connector_id not in connectors:
                connectors[pool.connector_id] = session.get(Connectors, pool.connector_id)

    for host in hosts:
        try:
            names |= list_kvm_names(host)
        except Exception as exception:
            warnings.append(f"The hypervisor {host.hostname} could not be listed: {exception}")
    for connector in connectors.values():
        if connector is None:
            continue
        try:
            names |= list_cloudstack_names(connector)
        except Exception as exception:
            warnings.append(f"The connector {connector.name} could not be listed: {exception}")
    if not hosts and not connectors:
        warnings.append("No hypervisor and no connector is configured: the list is not trusted.")
    elif not names:
        warnings.append("No virtual machine was found: the list is not trusted.")
    return names, warnings
