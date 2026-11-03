from datetime import datetime
import json
import time

from app.routes import host as host_route
from app.routes import pool as pool_route
from app.routes import backup_policy as policy_route
from app.routes import external_hooks as hook_route
from app import task_helper, vault
from app.database import Pools
from app.hooks.hook_client import HookClient
from app.hooks.slack import SlackClient
from app import notifier
from app.logging import logged


def __from_hook_id(hook_id) -> HookClient:
    hook = hook_route.get_hook_by_id(hook_id)

    # Stub
    # Future : prodiver = hook.provider
    provider = "slack"

    match provider:
        case "slack":
            return SlackClient(vault.decrypt(hook.value))
        case _:
            raise ValueError("Unsupported hook provider.")


def __from_pool_id(pool_id) -> tuple[Pools, None | HookClient]:
    pool = pool_route.filter_pool_by_id(pool_id)
    policy = policy_route.filter_policy_by_id(pool.policy_id)
    # Hook is optional.
    if policy.externalhook:
        return pool, __from_hook_id(policy.externalhook)
    return pool, None


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


def __wait_for_end(task_id, task, state, attempts=10, pause=1.5):
    """The monitor (Flower) learns that a task ended a moment after the signal that runs this: without its end the card has no
    duration. It is read again until it says the state, a few seconds at most: the message goes out whatever happens."""
    for _ in range(attempts):
        if task.get("state") == state:
            break
        time.sleep(pause)
        try:
            fresh = json.loads(task_helper.get_task_info(task_id).decode('ascii'))
        except Exception:
            continue
        task.update({key: fresh[key] for key in ("state", "runtime", "started", "timestamp") if key in fresh})


@logged()
def on_task_success(task_id, message):
    task, client = __from_task_id(task_id)
    if client is not None:
        __wait_for_end(task_id, task, "SUCCESS")
        # This runs because the task ended: if the monitor is still a step behind, the state is the one of the signal.
        task["state"] = "SUCCESS"
        client.on_task_success(task, message)


@logged()
def on_task_failure(task_id, message):
    task, client = __from_task_id(task_id)
    if client is not None:
        __wait_for_end(task_id, task, "FAILURE")
        task["state"] = "FAILURE"
        client.on_task_failure(task, message)


# TODO Direct event binding here ?
@logged()
def on_pool(result, pool_id, received):
    pool, client = __from_pool_id(pool_id)
    if client is not None:
        # Build success and failure lists based on chord tasks results
        success_list = []
        failure_list = []
        # Machines not backed up because they are not running: told apart, they are not failures.
        skipped_list = []
        # Machines whose backups wait for an administrator (a disk that needs attention): not a new failure.
        blocked_list = []

        for item in result:
            if isinstance(item, dict):
                if item.get('status') == 'success':
                    vm = item["info"]
                    success_list.append(vm)
                elif item.get('status') == 'skipped':
                    skipped_list.append(item["info"])
                # TODO else ?
            elif "NEEDS ATTENTION" in str(item):
                blocked_list.append(str(item))
            else:
                # The result of a task that failed: its error, as text or as an exception.
                failure_list.append(item)

        client.on_pool(pool, success_list, failure_list, received, skipped_list, blocked_list)


class __StubPool:
    name = "Notification test pool"


@logged()
def test(hook_id):
    client = __from_hook_id(hook_id)

    task = {
        "runtime": 4 * 60 + 20,
        "state": "TEST",
        "started": 1746709361,
        "name": "Notification test task",
        'args': [{
            'name': "Notification test VM"
        }]
    }

    message = "Notification test message"
    client.on_task_success(task, message)
    client.on_task_failure(task, message)

    # TODO More accurate stub for list item.
    received = datetime.now()
    client.on_pool(__StubPool(), [task], [], received)
    client.on_pool(__StubPool(), [], [task], received)
    client.on_pool(
        __StubPool(), [task, task], ["ChordError: backup of Notification test VM failed (disk missing)"], received,
        [{"name": "Notification test VM (off)"}],
        ["BackupStateError: NEEDS ATTENTION: Notification test VM is blocked until an administrator clears it"])
    # And the other messages of BackROLL, in the same look.
    notifier.send_examples(hook_id)
