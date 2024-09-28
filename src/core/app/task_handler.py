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

#!/usr/bin/env python
import sys
from datetime import datetime
import json
import requests
import time

from app import celery
from celery.signals import task_failure, task_success

from app.backup_tasks import single_backup
from app.routes import host as host_route
from app.routes import pool as pool_route
from app.routes import backup_policy as policy_route
from app.routes import external_hooks as hook_route

from app import restore

from app.webhooks import slack


def list_running_tasks(application):
    return application.active()


def retrieve_task_info(task_id):
    response = requests.get(f"http://flower:5555/api/task/info/{task_id}")
    return response.content


def eval_python_data(data_string):
    data_string = str(data_string)
    data_string_len = len(data_string)
    for _ in range(0, data_string_len):
        try:
            return eval(data_string)
        except SyntaxError as e:
            column = e.offset
            if column == 0:
                data_string = data_string[1:]
            elif column == len(data_string) - 1:
                data_string = data_string[:column]
            else:
                data_string = data_string[:column-1] + data_string[column:]
        except Exception as e:
            raise ValueError(
                f"With Python {sys.version}, failed to fix data string “{data_string}”.")


def ensure_dict(value):
    if isinstance(value, dict):
        return value

    if isinstance(value, tuple) or isinstance(value, list):
        return ensure_dict(value[0])

    return None


def ensure_json_serializable(value):
    def typeAsString(object):
        return str(type(object))

    return json.loads(json.dumps(value, default=typeAsString))


def parse_task_args(args):
    return ensure_json_serializable(ensure_dict(eval_python_data(args)))


def convert(seconds):
    if type(seconds) != type(None):
        seconds = seconds % (24 * 3600)
        hour = seconds // 3600
        seconds %= 3600
        minutes = seconds // 60
        seconds %= 60
        return "%d:%02d:%02d" % (hour, minutes, seconds)
    else:
        return "Unable to retrieve runtime"


##################################
# Handle task result and output to webhook (if any)
@celery.task(name='Handle task success', max_retries=None)
def handle_task_success(task_id, msg):

    task_result = json.loads(retrieve_task_info(task_id).decode('ascii'))
    task_args = parse_task_args(task_result['args'])

    if "host" in task_args:
        host = host_route.filter_host_by_id(task_args['host'])
        pool = pool_route.filter_pool_by_id(host.pool_id)
        policy = policy_route.filter_policy_by_id(pool.policy_id)
    else:
        pool = pool_route.filter_pool_by_id(task_args["pool_id"])
        policy = policy_route.filter_policy_by_id(pool.policy_id)

    if policy.externalhook:
        hook = hook_route.filter_external_hook_by_id(policy.externalhook)

        # Future feature : support multiple external hook providers.
        # if hook.provider.lower() == "slack" and hook.value:
        if hook.value:
            time.sleep(10)
            context_smiley = "white_check_mark"
            alerting = ""
            duration_time = f"{convert(task_result['runtime'])}"
            block_msg = {
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"{alerting}*{msg}*"
                        }
                    },
                    {
                        "type": "divider"
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f"*Target*\n{task_args['name']}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*State*\n{task_result['state']} :{context_smiley}:"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Created on*\n{datetime.fromtimestamp(task_result['started'])}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Duration*\n{duration_time}"
                            }
                        ]
                    },
                    {
                        "type": "divider"
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": f"*TYPE*: {task_result['name']}"
                            }
                        ]
                    }
                ]
            }
            slack.connector(hook, block_msg['blocks'])


@celery.task(name='Handle task failure')
def handle_task_failure(task_id, msg):

    task_result = json.loads(retrieve_task_info(task_id).decode('ascii'))
    task_args = parse_task_args(task_result['args'])

    host = host_route.filter_host_by_id(task_args['host'])
    pool = pool_route.filter_pool_by_id(host.pool_id)
    policy = policy_route.filter_policy_by_id(pool.policy_id)

    if policy.externalhook:
        hook = hook_route.filter_external_hook_by_id(policy.externalhook)

        # Future feature : support multiple external hook providers.
        # if hook.provider.lower() == "slack" and hook.value:
        if hook.value:
            time.sleep(10)
            context_smiley = "x"
            alerting = "<!channel> "
            duration_time = "N/A"
            block_msg = {
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"{alerting}*{msg}*"
                        }
                    },
                    {
                        "type": "divider"
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f"*Target*\n{task_args['name']}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*State*\n{task_result['state']} :{context_smiley}:"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Created on*\n{datetime.fromtimestamp(task_result['started'])}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Duration*\n{duration_time}"
                            }
                        ]
                    },
                    {
                        "type": "divider"
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": f"*TYPE*: {task_result['name']}"
                            }
                        ]
                    }
                ]
            }
            slack.connector(hook, block_msg['blocks'])


@task_success.connect(sender=single_backup.single_vm_backup)
def single_backup_success_handler(sender=None, body=None, *args,  **kwargs):
    handle_task_success.apply_async(
        args=(sender.request.id, "A new single VM backup job has ended"))


@task_failure.connect(sender=single_backup.single_vm_backup)
def single_backup_failure_handler(sender=None, body=None, *args,  **kwargs):
    handle_task_failure.apply_async(
        args=(sender.request.id, "A new single VM backup job has exited"))


@task_success.connect(sender=restore.restore_disk_vm)
def restore_backup_success_handler(sender=None, body=None, *args,  **kwargs):
    handle_task_success.apply_async(
        args=(sender.request.id, "A new diskfile restore job has ended"))


@task_failure.connect(sender=restore.restore_disk_vm)
def restore_backup_failure_handler(sender=None, body=None, *args,  **kwargs):
    handle_task_failure.apply_async(
        args=(sender.request.id, "A new diskfile restore job has ended"))


@celery.task()
def pool_backup_notification(result, pool_id):
    print(result, pool_id)

    # Retrieve pool's policy info
    pool = pool_route.filter_pool_by_id(pool_id)
    policy = policy_route.filter_policy_by_id(pool.policy_id)

    # No defined webhook - stopping here...
    if not policy.externalhook:
        return
    else:
        externalhook = hook_route.filter_external_hook_by_id(
            policy.externalhook)

        # Build success and failure lists based on chord tasks results
        success_list = []
        failure_list = []

        for item in result:
            if isinstance(item, dict):
                if item.get('status') == 'success':
                    success_list.append(item['info'])
            else:
                failure_list.append(item)

        # Future feature : support multiple external hook providers.
        # if externalhook.provider.lower() == "slack":
        slack.pool_notification(externalhook, success_list, failure_list, pool)
