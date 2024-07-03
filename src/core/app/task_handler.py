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
import re
from datetime import datetime
import json
from requests.auth import HTTPBasicAuth
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

# def cleanArgs(args):
#   argument = str(args)
#   print(args)
#   if ", ...,)" in argument:
#     argument = argument[len('('):-len(', ...,)')]
#     argument = argument + "}"
#   elif ", ...)" in argument:
#     argument = argument[len('('):-len(', ...)')]
#     argument = argument + "}"
#   elif ",)" in argument:
#     argument = argument[len('('):-len(',)')]
#   elif "}," in argument:
#     argument = argument.split("},", 1)[0]
#   argument = argument.replace("'", '"')
#   argument = argument.replace("True", 'true')
#   argument = argument.replace("False", 'false')
#   argument = argument.replace("(", '')
#   argument = argument.replace(")", '')

#   if"{...}" in argument:
#     argument = argument.replace("{...}", "")
  
#   if '...", ...}' in argument:
#     argument = argument.replace('...", ...}', '": "" }')

#   if "None" in argument:
#     argument = argument.replace("None", '"None"')

#   if", ...}" in argument:
#     argument = argument.replace(", ...}", ': ""')

#   argument.split("}", 1)[0]
#   return argument

def cleanArgs(args):
  argument = str(args)
  
  if ", 'displayvm': True" in argument :
      argument = argument[0: argument.index(", 'displayvm': True")]
      argument = argument + "})"

  while argument != '':
    try:
        obj = eval(argument)
        break
    except SyntaxError as e:
        argument = argument[:e.offset - 1] + argument[e.offset:]
        continue
  
  if isinstance(obj,dict):
    return json.dumps(obj)
  elif isinstance(obj,tuple) or isinstance(obj,list):
    return json.dumps(obj[0])

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

  task_result = retrieve_task_info(task_id).decode('ascii')  
  text = json.loads(task_result)['args']
  cleanedtext = cleanArgs(text)
  task_args = json.loads(cleanedtext)

  if "host" in task_args:
    host = host_route.filter_host_by_id(task_args['host'])
    pool = pool_route.filter_pool_by_id(host.pool_id)
    policy = policy_route.filter_policy_by_id(pool.policy_id)
  else:
    pool = pool_route.filter_pool_by_id(task_args["pool_id"])
    policy = policy_route.filter_policy_by_id(pool.policy_id)
  
  if policy.externalhook:
    hook = hook_route.filter_external_hook_by_id(policy.externalhook)

    if hook.provider.lower() == "slack" and hook.value:
      time.sleep(10)
      task_result = retrieve_task_info(task_id).decode('ascii')
      text = json.loads(task_result)['args']
      cleanedtext = cleanArgs(text)
      task_args = json.loads(cleanedtext)
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
      slack.connector(hook, block_msg['blocks'])


@celery.task(name='Handle task failure')
def handle_task_failure(task_id, msg):

  task_result = retrieve_task_info(task_id).decode('ascii')
  text = json.loads(task_result)['args']
  print("DEBUG TASK Failure: text: " + text)
  cleanedtext = cleanArgs(text)
  task_args = json.loads(cleanedtext)

  host = host_route.filter_host_by_id(task_args['host'])
  pool = pool_route.filter_pool_by_id(host.pool_id)
  policy = policy_route.filter_policy_by_id(pool.policy_id)
  hook = hook_route.filter_external_hook_by_id(policy.externalhook)

  if hook.provider.lower() == "slack" and hook.value:
    time.sleep(10)
    task_result = retrieve_task_info(task_id).decode('ascii')
    text = json.loads(task_result)['args']
    
    print(text)
    
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
    slack.connector(hook, block_msg['blocks'])


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

  # Retrieve pool's policy info
  pool = pool_route.filter_pool_by_id(pool_id)
  policy = policy_route.filter_policy_by_id(pool.policy_id)

  # No defined webhook - stopping here...
  if not policy.externalhook: return
  else:
    externalhook = hook_route.filter_external_hook_by_id(policy.externalhook)

    # Build success and failure lists based on chord tasks results
    success_list = []
    failure_list = []

    for item in result:
      if isinstance(item, dict):
        if item.get('status') == 'success':
          success_list.append(item['info'])
      else:
          failure_list.append(item)

    if externalhook.provider.lower() == "slack":
      slack.pool_notification(externalhook, success_list, failure_list, pool)