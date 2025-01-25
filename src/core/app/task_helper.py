import redis
import json
from app import patch

def manage_task_args(task, redis_client = None):
    is_client_local = redis_client is None

    if is_client_local:
        redis_client = redis.Redis(host="redis", port=6379, db=0)
    
    celery_task_bytes = redis_client.get(f"celery-task-meta-{task["uuid"]}")
    if celery_task_bytes is not None:
        celery_task_json = celery_task_bytes.decode()
        celery_task = json.loads(celery_task_json)
        task["args"] = celery_task["args"]
    else:
        task["args"] = patch.parse_python_data(task["args"])

    if is_client_local:
        redis_client.quit()


def manage_task_dict_args(task_dict):
    redis_client = redis.Redis(host="redis", port=6379, db=0)

    for task in task_dict.values():
        manage_task_args(task, redis_client)
    
    redis_client.quit()
