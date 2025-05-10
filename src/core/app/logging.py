import logging
from celery.app.log import TaskFormatter


logging.basicConfig(level=logging.INFO)

root_logger = logging.getLogger()
root_handler = root_logger.handlers[0]
root_handler.setFormatter(TaskFormatter(
    '%(asctime)s %(task_name)s(%(task_id)s) [%(levelname)s] [%(name)s] %(message)s'))

def __getLogger(f):
    # Note that getLogger() is cached.
    return logging.getLogger(f"{__name__}.{f.__qualname__}")


def __bounded(first, current):
    logger = __getLogger(first)

    def last(*args, **kwargs):
        logger.info("before")
        value = current(*args, **kwargs)
        logger.info("after")
        return value
    return last


def __injected(first, current):
    if "logger" in first.__code__.co_varnames:
        def last(*args, **kwargs):
            return current(*args, logger=__getLogger(first), **kwargs)
        return last
    return current


def logged(bounds=True, logger=True):
    bounded = bounds
    injected = logger

    def decorator(first):
        current = first

        if bounded:
            current = __bounded(first, current)

        if injected:
            current = __injected(first, current)

        return current
    return decorator
