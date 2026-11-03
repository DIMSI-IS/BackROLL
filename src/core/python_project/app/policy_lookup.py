"""The backup policy of a virtual machine: through its hypervisor, or through its pool when it has none
(a CloudStack machine that is stopped has no hypervisor)."""

from app.routes import backup_policy, host, pool


def policy_of(virtual_machine: dict):
    pool_id = (host.filter_host_by_id(virtual_machine["host"]).pool_id
               if virtual_machine.get("host") else virtual_machine["pool_id"])
    return backup_policy.filter_policy_by_id(pool.filter_pool_by_id(pool_id).policy_id)
