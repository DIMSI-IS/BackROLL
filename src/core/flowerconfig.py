from app.environment import get_redis_host, get_persistent_directory

# Broker
broker = f'redis://{get_redis_host()}:6379/0'

# Persistency
persistent = True
db = (get_persistent_directory() / "flower/database").as_posix()
