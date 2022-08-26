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

#!/usr/bin/env python
import os
from datetime import datetime
import json
from requests.auth import HTTPBasicAuth
import requests
import time

from app import app
from app import celery as celeryWorker
from app import celery

from celery.signals import task_failure, task_success
from celery.result import AsyncResult
from celery import Celery, states
from celery.exceptions import Ignore

from app.backup_tasks import single_backup
from app.backup_tasks import pool_backup
from app.routes import kickstart_backup
from app.routes import pool as pool_routes

from app import restore

from app import database

from app.slack import messager

def list_running_tasks(application):
    return application.active()

def retrieve_task_info(task_id):
  response = requests.get(f"http://flower:5555/api/task/info/{task_id}", auth=HTTPBasicAuth(os.getenv('FLOWER_USER'), os.getenv('FLOWER_PASSWORD')))
  return response.content


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
# Handle task result and output to slack
@celery.task(name='Handle task success', max_retries=None)
def handle_task_success(task_id, msg):
  time.sleep(10)
  task_result = retrieve_task_info(task_id).decode('ascii')
  text = json.loads(task_result)['args']
  left = '{'
  right = '}'
  arguments = "{" + text[text.index(left)+len(left):text.index(right)] + "}"
  arguments = arguments.replace("'", '"')
  task_args = json.loads(arguments)
  context_smiley = "white_check_mark"
  alerting = ""
  duration_time = f"{convert(json.loads(task_result).get('runtime'))}"
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
            "text": f"*State*\n{json.loads(task_result)['state']} :{context_smiley}:"
          },
          {
            "type": "mrkdwn",
            "text": f"*Created on*\n{datetime.fromtimestamp(json.loads(task_result)['started'])}"
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
            "text": f"*TYPE*: {json.loads(task_result)['name']}"
          }
        ]
      }
    ]
  }
  messager.slack_notification(block_msg['blocks'])


@celery.task(name='Handle task failure')
def handle_task_failure(task_id, msg):
  time.sleep(5)
  task_result = retrieve_task_info(task_id).decode('ascii')
  text = json.loads(task_result)['args']
  left = "{"
  right = "}"
  arguments = "{" + text[text.index(left)+len(left):text.index(right)] + "}"
  arguments = arguments.replace("(", '')
  arguments = arguments.replace(")", '')
  arguments = arguments.replace("'", '"')
  task_args = json.loads(arguments)
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
            "text": f"*State*\n{json.loads(task_result)['state']} :{context_smiley}:"
          },
          {
            "type": "mrkdwn",
            "text": f"*Created on*\n{datetime.fromtimestamp(json.loads(task_result)['started'])}"
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
            "text": f"*TYPE*: {json.loads(task_result)['name']}"
          }
        ]
      }
    ]
  }
  messager.slack_notification(block_msg['blocks'])


@task_success.connect(sender=single_backup.single_vm_backup)
def single_backup_success_handler(sender=None, body=None, *args,  **kwargs):
    handle_task_success.apply_async(args=(sender.request.id, "A new single VM backup job has ended"))

@task_failure.connect(sender=single_backup.single_vm_backup)
def single_backup_failure_handler(sender=None, body=None, *args,  **kwargs):
    handle_task_failure.apply_async(args=(sender.request.id, "A new single VM backup job has exited"))

@task_success.connect(sender=restore.restore_disk_vm)
def restore_backup_success_handler(sender=None, body=None, *args,  **kwargs):
    handle_task_success.apply_async(args=(sender.request.id, "A new diskfile restore job has ended"))

@task_failure.connect(sender=restore.restore_disk_vm)
def restore_backup_failure_handler(sender=None, body=None, *args,  **kwargs):
    handle_task_failure.apply_async(args=(sender.request.id, "A new diskfile restore job has ended"))

@celery.task()
def pool_backup_notification(result, pool_id):
  print(result, pool_id)

  pool = pool_routes.filter_pool_by_id(pool_id)

  # Build success and failure lists based on chord tasks results
  success_list = []
  failure_list = []

  for item in result:
    if isinstance(item, dict):
      if item.get('status') == 'success':
        success_list.append(item['info'])

  inital_vm_list = kickstart_backup.getVMtobackup(pool_id)
  for item in inital_vm_list:
    if item not in success_list:
      failure_list.append(item)

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
    messager.slack_notification(slack_block['blocks'])
  except:
    raise