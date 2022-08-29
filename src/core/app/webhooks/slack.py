## Licensed to the Apache Software Foundation (ASF) under one
## or more contributor license agreements.  See the NOTICE file
## distributed with this work for additional information
## regarding copyright ownership.  The ASF licenses this file
## to you under the Apache License, Version 2.0 (the
## "License"); you may not use this file except in compliance
## with the License.  You may obtain a copy of the License at
##
##   http://www.apache.org/licenses/LICENSE-2.0
##
## Unless required by applicable law or agreed to in writing,
## software distributed under the License is distributed on an
## "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
## KIND, either express or implied.  See the License for the
## specific language governing permissions and limitations
## under the License.

import os
from slack_sdk.webhook import WebhookClient
from slack_sdk.errors import SlackApiError

def connector(hook, payload):
  webhook = WebhookClient(hook.value)
  try:
      webhook.send(text="fallback", blocks=payload)
  except SlackApiError as e:
      assert e.response["ok"] is False
      assert e.response["error"]
      print(f"Got an error: {e.response}")

def pool_notification(externalhook, success_list, failure_list, pool):
  # Build slack block message
  alert = ''
  if len(failure_list) > 0:
    alert = '<!channel> '

  slack_block = {
    "blocks": [
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
            "text": f"{alert}*{pool.name}*"
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
          "url": f"{os.getenv('BASE_URL')}/admin/tasks/backup",
          "action_id": "button-action"
        }
      }
    ]
  }

  try:
    connector(hook, slack_block['blocks'])
  except:
    raise