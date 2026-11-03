"""The tasks of the demo used by the tests of the interface are always the tasks of today.

The CI failed one night: it ran just after midnight (Paris), the demo placed its tasks a few hours back, they belonged
to yesterday, and the page of the day showed none. The clock is given to the demo here, at the hours that matter.
"""

import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "screenshots"))

pytest.importorskip("fastapi")
zoneinfo = pytest.importorskip("zoneinfo")

import mock_server  # noqa: E402


@pytest.fixture(scope="module")
def zone():
    try:
        return zoneinfo.ZoneInfo("Europe/Paris")
    except Exception:
        pytest.skip("no time zone database on this machine (pip install tzdata)")


@pytest.mark.parametrize("hour,minute,second", [(0, 0, 30), (0, 1, 0), (0, 6, 0), (0, 30, 0), (3, 0, 0), (12, 0, 0), (23, 59, 59)])
def test_every_task_of_the_demo_is_of_the_day_of_the_browser(zone, hour, minute, second):
    now = datetime(2026, 10, 20, hour, minute, second, tzinfo=zone)
    tasks = mock_server.tasks_backup(now)
    assert len(tasks) == 9
    for task in tasks:
        if task["started"] is not None:
            assert datetime.fromtimestamp(task["started"], zone).date() == now.date(), (hour, minute, task["args"])
        assert task["started"] is None or task["started"] <= now.timestamp()


def test_the_demo_follows_the_zone_asked_by_the_environment(zone, monkeypatch):
    monkeypatch.setenv("MOCK_TIMEZONE", "Pacific/Auckland")
    try:
        auckland = zoneinfo.ZoneInfo("Pacific/Auckland")
    except Exception:
        pytest.skip("no time zone database")
    now = datetime(2026, 10, 20, 0, 5, tzinfo=auckland)
    for task in mock_server.tasks_backup(now):
        if task["started"] is not None:
            assert datetime.fromtimestamp(task["started"], auckland).date() == now.date()
