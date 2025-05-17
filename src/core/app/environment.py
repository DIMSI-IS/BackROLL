import os


class MissingEnvironmentVariableException(Exception):
    def __init__(self, message):
        super().__init__(message)


def get_env_var(name, allow_blank=False, allow_undefined=False):
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
