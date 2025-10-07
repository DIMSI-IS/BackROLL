from app.environment import get_redis_host, get_persistent_directory

# Broker
broker = f'redis://{get_redis_host()}:6379/0'

# Persistency
persistent = True
__directory = get_persistent_directory() / "flower"
__directory.mkdir(parents=True, exist_ok=True)
db = (__directory / "database").as_posix()
