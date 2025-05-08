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

from datetime import datetime
import os
import time
from app.hooks.hook_client import HookClient, convert
from slack_sdk.webhook import WebhookClient
from slack_sdk.errors import SlackApiError

from app.patch import make_path


class SlackClient(HookClient):
    def __init__(self, value):
        self.__inner = WebhookClient(value)

    def __send(self, blocks):
        try:
            self.__inner.send(blocks=blocks)
        except SlackApiError as e:
            assert e.response["ok"] is False
            assert e.response["error"]
            print(f"Got an error: {e.response}")

    def on_task_success(self, task, message):
        task_arg = task['args'][0]

        time.sleep(10)
        context_smiley = "white_check_mark"
        alerting = ""
        duration_time = f"{convert(task['runtime'])}"
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{alerting}*{message}*"
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
                        "text": f"*Target*\n{task_arg['name']}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*State*\n{task['state']} :{context_smiley}:"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Created on*\n{datetime.fromtimestamp(task['started'])}"
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
                        "text": f"*TYPE*: {task['name']}"
                    }
                ]
            }
        ]

        self.__send(blocks)

    def on_task_failure(self, task, message):
        task_arg = task['args'][0]

        time.sleep(10)
        context_smiley = "x"
        alerting = "<!channel> "
        duration_time = "N/A"
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{alerting}*{message}*"
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
                        "text": f"*Target*\n{task_arg['name']}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*State*\n{task['state']} :{context_smiley}:"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Created on*\n{datetime.fromtimestamp(task['started'])}"
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
                        "text": f"*TYPE*: {task['name']}"
                    }
                ]
            }
        ]

        self.__send(blocks)

    def on_pool(self, pool, success_list, failure_list):
        alerting = ''
        if len(failure_list) > 0:
            alerting = '<!channel> '

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "Summary of your pool backup job"
                }
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"{alerting}*{pool.name}*"
                    }
                ]
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": ":white_check_mark:"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*{len(success_list)}* Successful backup(s)"
                    }
                ]
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": ":x:"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*{len(failure_list)}* Failed backup(s)"
                    }
                ]
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Review all backup tasks :arrow_right:"
                },
                "accessory": {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "By clicking here",
                    },
                    "value": "click_me_123",
                    # The notification may not be displayed in Slack if the URL is invalid.
                    "url": make_path(os.getenv('FRONT_URL'), "admin/tasks/backup"),
                    "action_id": "button-action"
                }
            }
        ]

        self.__send(blocks)
