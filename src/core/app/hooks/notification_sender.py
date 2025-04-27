import json

from app.routes import host as host_route
from app.routes import pool as pool_route
from app.routes import backup_policy as policy_route
from app.routes import external_hooks as hook_route
from app import task_helper
from app.database import Pools
from app.hooks.hook_client import HookClient
from app.hooks.slack import SlackClient


def __from_hook_id(hook_id) -> HookClient:
    hook = hook_route.get_hook_by_id(hook_id)

    # Stub
    # Future : prodiver = hook.provider
    provider = "slack"

    match provider:
        case "slack":
            return SlackClient(hook.value)
        case _:
            raise ValueError("Unsupported hook provider.")


def __from_pool_id(pool_id) -> tuple[Pools, None | HookClient]:
    pool = pool_route.filter_pool_by_id(pool_id)
    policy = policy_route.filter_policy_by_id(pool.policy_id)
    # Hook is optional.
    if policy.externalhook:
        return pool, __from_hook_id(policy.externalhook)


def __from_task_id(task_id) -> tuple[dict, None | HookClient]:
    task = json.loads(task_helper.get_task_info(task_id).decode('ascii'))
    task_helper.manage_task_args(task)
    task_arg = task['args'][0]

    # Why ? Some tasks have no host ? Or it was truncated ?
    if "host" in task_arg:
        host = host_route.filter_host_by_id(task_arg['host'])
        pool_id = host.pool_id
    else:
        pool_id = task_arg["pool_id"]

    return task, __from_pool_id(pool_id)[1]


def on_task_success(task_id, message):
    task, client = __from_task_id(task_id)
    if client is not None:
        client.on_task_success(task, message)


def on_task_failure(task_id, message):
    task, client = __from_task_id(task_id)
    if client is not None:
        client.on_task_failure(task, message)


def on_pool(result, pool_id):
    pool, client = __from_pool_id(pool_id)
    if client is not None:
        # Build success and failure lists based on chord tasks results
        success_list = []
        failure_list = []

        for item in result:
            if isinstance(item, dict):
                if item.get('status') == 'success':
                    success_list.append(item['info'])
            else:
                failure_list.append(item)

        client.on_pool(pool, success_list, failure_list)
