# TODO Use a lib ?
def convert(seconds):
    if type(seconds) != type(None):
        seconds = seconds % (24 * 3600)
        hour = seconds // 3600
        seconds %= 3600
        minutes = seconds // 60
        seconds %= 60
        return "%d:%02d:%02d" % (hour, minutes, seconds)
    else:
        return "Unable to retrieve runtime"


def task_duration(task):
    """Seconds the task took, or None when nothing says it.

    Flower gives the runtime of a task that succeeded. For a task that failed it gives none, but it knows when the task
    started and the time of its last event, the failure.
    """
    runtime = task.get("runtime")
    if runtime is not None:
        return runtime
    started, ended = task.get("started"), task.get("timestamp")
    if started is not None and ended is not None and ended >= started:
        return ended - started
    return None


def format_duration(task, unknown):
    seconds = task_duration(task)
    return convert(seconds) if seconds is not None else unknown


class HookClient:
    def on_task_success(self, task, message):
        pass

    def on_task_failure(self, task, message):
        pass

    def on_pool(self, pool, success_list, failure_list, received, skipped_list=None, blocked_list=None):
        pass
