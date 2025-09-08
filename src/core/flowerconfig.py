from app.environment import get_env_var

# Broker
broker = f'redis://{get_env_var("REDIS_URL")}:6379/0'

# Persistency
persistent = True
db = '/root/flower/database'
