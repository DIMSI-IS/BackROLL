import os

# Broker
broker = 'redis://redis:6379/0'

# Basic auth
basic_auth = [f"{os.getenv('FLOWER_USER')}:{os.getenv('FLOWER_PASSWORD')}"]
