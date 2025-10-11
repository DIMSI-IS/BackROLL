from redis import Redis
from app.environment import get_redis_host


def new_redis_client():
    return Redis(host=get_redis_host(), port=6379)
