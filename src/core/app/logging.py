from logging import INFO, getLogger, Formatter, StreamHandler


class ConditionalFormatter(Formatter):
    def __init__(self, formatter, task_formatter):
        self.formatter = formatter
        self.task_formatter = task_formatter
        try:
            from celery._state import get_current_task
            self.get_current_task = get_current_task
        except ImportError:
            self.get_current_task = lambda: None

    def format(self, record):

        # Task formatter
        task = self.get_current_task()
        if task and task.request:
            record.__dict__.update(
                task_id=task.request.id, task_name=task.name)
            return self.task_formatter.format(record)

        # Generic formatter
        return self.formatter.format(record)


def __configure_logger(f):
    name = f"{f.__module__}.{f.__qualname__}"

    # Note that getLogger() is cached.
    logger = getLogger(name)

    # Shows the logs.
    logger.setLevel(INFO)

    custom_handler = StreamHandler()
    custom_handler.setFormatter(
        ConditionalFormatter(
            Formatter(
                "%(asctime)s | %(levelname)s | %(name)s() | %(message)s"),
            Formatter(
                "%(asctime)s | %(levelname)s | %(task_name)s(%(task_id)s) | %(name)s() | %(message)s"),
        )
    )
    logger.addHandler(custom_handler)

    # Prevents logging a second time with the default celery formatter.
    logger.propagate = False

    return logger


def __bounded(_, current, logger):
    def last(*args, **kwargs):
        logger.info("before")
        value = current(*args, **kwargs)
        logger.info("after")
        return value
    return last


def __injected(first, current, logger):
    if "logger" in first.__code__.co_varnames:
        def last(*args, **kwargs):
            return current(*args, logger=logger, **kwargs)
        return last
    return current


def logged(bounds=True, logger=True):
    bounded = bounds
    injected = logger

    def decorator(first):
        logger = __configure_logger(first)
        current = first

        if bounded:
            current = __bounded(first, current, logger)

        if injected:
            current = __injected(first, current, logger)

        return current
    return decorator
