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

from app.initialized import celery_app
from celery.signals import task_failure, task_success

from app.backup_tasks import single_backup

from app import restore

from app.hooks import notification_sender


def list_running_tasks(application):
    return application.active()


@celery_app.task(name='Handle task success', max_retries=None)
def handle_task_success(task_id, msg):
    notification_sender.on_task_success(task_id, msg)


@celery_app.task(name='Handle task failure')
def handle_task_failure(task_id, msg):
    notification_sender.on_task_failure(task_id, msg)


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


@celery_app.task()
def pool_backup_notification(result, pool_id):
    notification_sender.on_pool(result, pool_id)
