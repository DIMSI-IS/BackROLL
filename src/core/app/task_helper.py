import requests
import json

from app.environment import get_flower_url
from app.patch import parse_python_data
from app.redis import new_redis_client


def get_task_info(task_id):
    response = requests.get(
        f"http://{get_flower_url()}:5555/api/task/info/{task_id}")
    return response.content


def manage_task_args(task, redis_client=None):
    is_client_local = redis_client is None

    if is_client_local:
        redis_client = new_redis_client()

    celery_task_bytes = redis_client.get(f"celery-task-meta-{task["uuid"]}")
    if celery_task_bytes is not None:
        celery_task_json = celery_task_bytes.decode()
        celery_task = json.loads(celery_task_json)
        task["args"] = celery_task["args"]
    else:
        task["args"] = parse_python_data(task["args"])

    if is_client_local:
        redis_client.quit()


def manage_task_dict_args(task_dict):
    redis_client = new_redis_client()

    for task in task_dict.values():
        manage_task_args(task, redis_client)

    redis_client.quit()
