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


class HookClient:
    def on_task_success(self, task, message):
        pass

    def on_task_failure(self, task, message):
        pass

    def on_pool(self, pool, success_list, failure_list, received):
        pass
