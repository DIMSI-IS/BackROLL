"""The duration in the Slack cards of a task: given for a success and for a failure, even when the monitor (Flower) learns the end
of the task a moment after the signal that sends the card (anomaly A-019: « Unable to retrieve runtime »)."""

import json
from types import SimpleNamespace

import pytest

pytest.importorskip("slack_sdk")

from app.hooks import hook_client, notification_sender, slack  # noqa: E402


def duration_field(blocks):
    for block in blocks:
        for field in block.get("fields", []):
            if field["text"].startswith("*Duration*"):
                return field["text"].split("\n", 1)[1]
    raise AssertionError("no duration in the card")


def card(monkeypatch, method, task):
    sent = []
    client = slack.SlackClient("https://hooks.slack.test/services/x")
    monkeypatch.setattr(slack.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(slack.SlackClient, "_SlackClient__send", lambda self, blocks: sent.append(blocks))
    getattr(client, method)(task, "message")
    return duration_field(sent[0])


BASE = {"args": [{"name": "web-01"}], "name": "Single_VM_Backup", "started": 1000.0}


def test_the_duration_of_a_task_that_succeeded_is_its_runtime():
    assert hook_client.task_duration({"runtime": 92.4, "started": 1000.0, "timestamp": 1500.0}) == 92.4


def test_the_duration_of_a_task_that_failed_is_the_time_between_its_start_and_its_failure():
    assert hook_client.task_duration({"runtime": None, "started": 1000.0, "timestamp": 1012.5}) == 12.5


@pytest.mark.parametrize("task", [{}, {"started": 1000.0}, {"started": 1000.0, "timestamp": 900.0}])
def test_without_what_it_takes_the_duration_is_unknown(task):
    assert hook_client.task_duration(task) is None


def test_the_card_of_a_success_shows_the_duration(monkeypatch):
    assert card(monkeypatch, "on_task_success", dict(BASE, state="SUCCESS", runtime=92.0)) == "0:01:32"


def test_the_card_of_a_success_without_duration_still_says_so(monkeypatch):
    assert card(monkeypatch, "on_task_success", dict(BASE, state="SUCCESS", runtime=None)) == "Unable to retrieve runtime"


def test_the_card_of_a_failure_shows_the_time_it_took(monkeypatch):
    task = dict(BASE, state="FAILURE", runtime=None, timestamp=1065.0)
    assert card(monkeypatch, "on_task_failure", task) == "0:01:05"


def test_the_card_of_a_failure_without_dates_keeps_the_not_available_mark(monkeypatch):
    assert card(monkeypatch, "on_task_failure", dict(BASE, state="FAILURE", runtime=None)) == "N/A"


# -- the monitor that is a moment late ---------------------------------------------------------------------------------

def monitor(monkeypatch, answers):
    """The successive answers of Flower for the same task."""
    pending = list(answers)
    asked = []
    monkeypatch.setattr(notification_sender.time, "sleep", lambda seconds: None)

    def get_task_info(task_id):
        asked.append(task_id)
        return json.dumps(pending.pop(0) if len(pending) > 1 else pending[0]).encode()
    monkeypatch.setattr(notification_sender.task_helper, "get_task_info", get_task_info)
    return asked


def hook_client_recording(told):
    return SimpleNamespace(on_task_success=lambda task, message: told.append(dict(task)),
                           on_task_failure=lambda task, message: told.append(dict(task)))


def test_the_card_waits_for_the_monitor_to_know_the_end_of_a_successful_task(monkeypatch):
    told = []
    started = {"state": "STARTED", "runtime": None, "started": 1000.0}
    ended = {"state": "SUCCESS", "runtime": 29.0, "started": 1000.0, "timestamp": 1029.0}
    # The first reading (the signal) said STARTED; the monitor says the end at the first new reading.
    asked = monitor(monkeypatch, [ended])
    monkeypatch.setattr(notification_sender, "__from_task_id", lambda task_id: (dict(started), hook_client_recording(told)))

    notification_sender.on_task_success("task", "ended")

    assert told[0]["state"] == "SUCCESS" and told[0]["runtime"] == 29.0
    assert len(asked) == 1


def test_the_card_of_a_failure_gets_the_time_of_the_failure_from_the_monitor(monkeypatch):
    told = []
    started = {"state": "STARTED", "runtime": None, "started": 1000.0}
    failed = {"state": "FAILURE", "runtime": None, "started": 1000.0, "timestamp": 1007.0}
    monitor(monkeypatch, [failed])
    monkeypatch.setattr(notification_sender, "__from_task_id", lambda task_id: (dict(started), hook_client_recording(told)))

    notification_sender.on_task_failure("task", "exited")

    assert told[0]["state"] == "FAILURE"
    assert hook_client.task_duration(told[0]) == 7.0


def test_a_monitor_that_never_answers_does_not_stop_the_message(monkeypatch):
    told = []
    asked = []
    monkeypatch.setattr(notification_sender.time, "sleep", lambda seconds: None)

    def broken(task_id):
        asked.append(task_id)
        raise ConnectionError("monitor down")
    monkeypatch.setattr(notification_sender.task_helper, "get_task_info", broken)
    monkeypatch.setattr(notification_sender, "__from_task_id",
                        lambda task_id: ({"state": "STARTED", "started": 1000.0}, hook_client_recording(told)))

    notification_sender.on_task_success("task", "ended")

    # It tried a few times, then sent the message with the state of the signal.
    assert told[0]["state"] == "SUCCESS" and 1 < len(asked) <= 10
