from redis import Redis
from app.environment import get_env_var


def new_redis_client():
    return Redis(host=get_env_var("REDIS_URL"), port=6379)
