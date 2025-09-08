from app.environment import get_env_var, get_flower_url

# Broker
broker = f'redis://{get_env_var("REDIS_URL")}:6379/0'

# Persistency
persistent = True
db = f'/root/{get_flower_url()}/database'
