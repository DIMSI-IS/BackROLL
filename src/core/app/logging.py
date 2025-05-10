import logging

logging.basicConfig(level=logging.INFO)


def __getLogger(f):
    # Note that getLogger() is cached.
    return logging.getLogger(f.__qualname__)


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
    def decorator(first):
        current = first

        if bounds:
            current = __bounded(first, current)

        if logger:
            current = __injected(first, current)

        return current
    return decorator
