import os
from pathlib import Path


class MissingEnvironmentVariableException(Exception):
    def __init__(self, message: str):
        super().__init__(message)


# TODO BACKROLL_ prefix ?
def get_env_var(name: str, allow_blank: bool = False, allow_undefined: bool = False):
    value = os.getenv(name)

    if value == None:
        if allow_undefined:
            return None
        raise MissingEnvironmentVariableException(
            f"Variable “{name}” must be defined.")

    value = value.strip()

    if value == "":
        if allow_blank:
            return ""
        raise MissingEnvironmentVariableException(
            f"Variable “{name}” must not be blank.")

    return value

# TODO Create a function for each env var here to prevent using strings everywhere ?
# TODO Use Pydantic settings ?


def get_redis_host():
    return "redis"


def get_flower_host():
    return "flower"


def get_persistent_directory():
    return Path("/root")
