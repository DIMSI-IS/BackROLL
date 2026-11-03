"""Creates a virtual machine in CloudStack, to receive restored disks."""

import math

import eventlet

from app.cloudstack import endpoint

JOB_TIMEOUT_SECONDS = 30 * 60
GIB = 1024 ** 3


class CloudStackError(Exception):
    pass


def to_gib(bytes_size: int) -> int:
    """CloudStack sizes are in GiB, a disk must not be smaller than its content."""
    return max(1, math.ceil(bytes_size / GIB))


def describe_error(exception: Exception) -> str:
    error = getattr(exception, "error", None)
    if isinstance(error, dict):
        return f"CloudStack error {error.get('cserrorcode', error.get('errorcode', ''))}: {error.get('errortext', exception)}"
    return str(exception)


def wait_for_job(cs, job_id: str):
    waited = 0
    while waited < JOB_TIMEOUT_SECONDS:
        job = cs.queryAsyncJobResult(jobid=job_id)
        if job["jobstatus"] == 1:
            return job.get("jobresult", {})
        if job["jobstatus"] == 2:
            result = job.get("jobresult", {})
            raise CloudStackError(result.get("errortext") or str(result))
        eventlet.sleep(2)
        waited += 2
    raise CloudStackError("The CloudStack job did not finish in time.")


def run_job(cs, command: str, **parameters):
    """Runs an asynchronous CloudStack command and waits for its result."""
    try:
        started = getattr(cs, command)(**parameters)
        if "jobid" in started:
            return wait_for_job(cs, started["jobid"])
        return started
    except CloudStackError:
        raise
    except Exception as exception:
        raise CloudStackError(describe_error(exception)) from exception


def merged(listing, key: str, domain_scope: dict, **parameters) -> list[dict]:
    """The offerings of the connector's account, plus the ones of the chosen domain.

    Asking for a domain only returns the offerings reserved to it, not the public ones.
    """
    items = {item["id"]: item for item in listing(**parameters).get(key, [])}
    if domain_scope:
        for item in listing(**parameters, **domain_scope).get(key, []):
            items.setdefault(item["id"], item)
    return list(items.values())


def get_options(connector, domain_id: str | None = None, account: str | None = None) -> dict:
    """What the user can choose to create the virtual machine.

    With a domain and an account, the templates and networks are the ones that account can use.
    """
    cs = endpoint.cloudstack_connector(connector)
    scope = {"domainid": domain_id, "account": account} if domain_id and account else {}
    domain_scope = {"domainid": domain_id} if domain_id else {}
    try:
        zones = cs.listZones(available=True).get("zone", [])
        domains = cs.listDomains(listall=True).get("domain", [])
        return {
            "domains": sorted(
                [{"id": d["id"], "name": d["name"], "path": d.get("path", d["name"])} for d in domains],
                key=lambda d: d["path"]),
            "zones": [{"id": z["id"], "name": z["name"]} for z in zones],
            "service_offerings": [
                {"id": o["id"], "name": o["name"], "cpus": o.get("cpunumber"),
                 "memory": o.get("memory")}
                for o in merged(cs.listServiceOfferings, "serviceoffering", domain_scope)],
            "templates": [
                {"id": t["id"], "name": t["name"], "zone_id": t.get("zoneid"),
                 "size": t.get("size")}
                for t in cs.listTemplates(templatefilter="executable", **scope).get("template", [])],
            "networks": [
                {"id": n["id"], "name": n["name"], "zone_id": n.get("zoneid"),
                 "cidr": n.get("cidr")}
                for n in cs.listNetworks(listall=True, **scope).get("network", [])],
            "disk_offerings": [
                {"id": d["id"], "name": d["name"],
                 "custom": bool(d.get("iscustomized"))}
                for d in merged(cs.listDiskOfferings, "diskoffering", domain_scope, listall=True)],
        }
    except Exception as exception:
        raise CloudStackError(describe_error(exception)) from exception


def list_accounts(connector, domain_id: str) -> list[dict]:
    cs = endpoint.cloudstack_connector(connector)
    try:
        accounts = cs.listAccounts(domainid=domain_id, listall=True).get("account", [])
        return [{"id": a["id"], "name": a["name"]} for a in accounts
                if a.get("state", "enabled") == "enabled"]
    except Exception as exception:
        raise CloudStackError(describe_error(exception)) from exception


def deploy_vm(cs, name: str, zone_id: str, service_offering_id: str, template_id: str,
              network_id: str | None, ip_address: str | None, root_disk_gib: int,
              domain_id: str | None = None, account: str | None = None) -> str:
    parameters = {
        "name": name,
        "displayname": name,
        "zoneid": zone_id,
        "serviceofferingid": service_offering_id,
        "templateid": template_id,
        "rootdisksize": root_disk_gib,
        # Started once to create the volumes, then stopped before they are replaced.
        "startvm": True,
    }
    if domain_id and account:
        # The virtual machine is created for another account, in another domain.
        parameters["domainid"] = domain_id
        parameters["account"] = account
    if network_id:
        if ip_address:
            parameters["iptonetworklist"] = [
                {"networkid": network_id, "ip": ip_address}]
        else:
            parameters["networkids"] = network_id

    result = run_job(cs, "deployVirtualMachine", **parameters)
    return result["virtualmachine"]["id"]


def create_and_attach_data_disk(cs, vm_id: str, name: str, zone_id: str,
                                disk_offering_id: str, size_gib: int,
                                domain_id: str | None = None, account: str | None = None):
    owner = {"domainid": domain_id, "account": account} if domain_id and account else {}
    volume = run_job(cs, "createVolume", name=name, zoneid=zone_id,
                     diskofferingid=disk_offering_id, size=size_gib, **owner)["volume"]
    run_job(cs, "attachVolume", id=volume["id"], virtualmachineid=vm_id)
    return volume["id"]


def stop_vm(cs, vm_id: str):
    run_job(cs, "stopVirtualMachine", id=vm_id)


def start_vm(cs, vm_id: str):
    run_job(cs, "startVirtualMachine", id=vm_id)


def destroy_vm(cs, vm_id: str):
    """Deletes a virtual machine with its disks. Only used for the machine a restore has just created."""
    volumes = cs.listVolumes(virtualmachineid=vm_id, listall=True).get("volume", [])
    data_volumes = [volume["id"] for volume in volumes if volume.get("type") != "ROOT"]
    parameters = {"id": vm_id, "expunge": True}
    if data_volumes:
        parameters["volumeids"] = ",".join(data_volumes)
    run_job(cs, "destroyVirtualMachine", **parameters)


def list_volumes(cs, vm_id: str) -> list[dict]:
    """The volumes of the virtual machine, the root volume first, then the data volumes in attach order."""
    volumes = cs.listVolumes(virtualmachineid=vm_id, listall=True).get("volume", [])
    return sorted(volumes, key=lambda volume: volume.get("deviceid", 0))


def get_storage_pool_id(cs, volume: dict) -> str:
    pools = cs.listStoragePools(listall=True, id=volume["storageid"]).get("storagepool")
    if not pools:
        raise CloudStackError(
            f"Storage pool of the volume {volume['name']} not found.")
    return pools[0]["id"]
