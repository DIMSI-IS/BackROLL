"""A connector that does not answer is told to the user, instead of silently dropping the machines that only CloudStack knows
(anomaly A-020: with an unreadable secret the list lost a machine and said nothing)."""

import json
from types import SimpleNamespace

import pytest

pytest.importorskip("app.routes.virtual_machine")

from app import vault  # noqa: E402
from app.routes import virtual_machine  # noqa: E402

CONNECTOR = SimpleNamespace(id="c1", name="CS", url="http://cs", login="k", password="enc1:x")
KVM_VM = {"uuid": "vm-kvm", "name": "web-01", "host": {"pool_id": "p1"}}


class FakeRedis:
    store = {}

    def set(self, key, value, ex=None):
        self.store[key] = value

    def get(self, key):
        return self.store.get(key)

    def quit(self):
        pass


@pytest.fixture
def redis(monkeypatch):
    FakeRedis.store = {}
    monkeypatch.setattr(virtual_machine, "new_redis_client", lambda: FakeRedis())
    return FakeRedis


@pytest.fixture
def listing(monkeypatch, redis):
    """handle_results with one hypervisor that answers and one connector."""
    group = SimpleNamespace(get=lambda: [{"host": {"pool_id": "p1"}, "virtualmachines": [dict(KVM_VM)]}])
    monkeypatch.setattr(virtual_machine.celery_app.GroupResult, "restore", lambda group_id: group)
    monkeypatch.setattr(virtual_machine.pool, "filter_pool_by_id", lambda pool_id: SimpleNamespace(connector_id="c1"))
    monkeypatch.setattr(virtual_machine.connectors, "filter_connector_by_id", lambda connector_id: CONNECTOR)


def test_the_machines_of_cloudstack_are_added_to_the_list_and_no_warning_is_kept(monkeypatch, listing, redis):
    cloudstack = [{"uuid": "vm-cs", "name": "i-2-1-VM"}]
    monkeypatch.setattr(virtual_machine.cs_manage_vm, "listAllVms", lambda connector: cloudstack)

    machines = virtual_machine.handle_results.run("group")

    assert sorted(m["uuid"] for m in machines) == ["vm-cs", "vm-kvm"]
    assert virtual_machine.read_warnings() == []


def test_an_unreadable_secret_is_a_warning_that_says_what_to_do_and_the_hypervisor_machines_are_still_listed(monkeypatch, listing, redis):
    def unreadable(connector):
        raise vault.SecretError("A stored secret could not be decrypted: the key changed. Type it again in the settings.")
    monkeypatch.setattr(virtual_machine.cs_manage_vm, "listAllVms", unreadable)

    machines = virtual_machine.handle_results.run("group")

    assert [m["uuid"] for m in machines] == ["vm-kvm"]
    (warning,) = virtual_machine.read_warnings()
    assert "connector CS" in warning and "type it again" in warning and "only CloudStack knows" in warning


def test_a_connector_that_does_not_answer_is_a_warning_with_the_reason(monkeypatch, listing, redis):
    def timeout(connector):
        raise TimeoutError("timed out")
    monkeypatch.setattr(virtual_machine.cs_manage_vm, "listAllVms", timeout)

    virtual_machine.handle_results.run("group")

    (warning,) = virtual_machine.read_warnings()
    assert "could not be listed" in warning and "timed out" in warning


def test_the_warnings_are_replaced_at_each_listing(monkeypatch, listing, redis):
    monkeypatch.setattr(virtual_machine.cs_manage_vm, "listAllVms", lambda connector: (_ for _ in ()).throw(TimeoutError("x")))
    virtual_machine.handle_results.run("group")
    assert len(virtual_machine.read_warnings()) == 1

    monkeypatch.setattr(virtual_machine.cs_manage_vm, "listAllVms", lambda connector: [])
    virtual_machine.handle_results.run("group")
    assert virtual_machine.read_warnings() == []


def test_a_redis_that_is_down_does_not_break_the_listing(monkeypatch, listing):
    def down():
        raise ConnectionError("redis down")
    monkeypatch.setattr(virtual_machine, "new_redis_client", down)
    monkeypatch.setattr(virtual_machine.cs_manage_vm, "listAllVms", lambda connector: [])

    assert [m["uuid"] for m in virtual_machine.handle_results.run("group")] == ["vm-kvm"]
    assert virtual_machine.read_warnings() == []


def test_the_route_of_the_warnings_answers_to_a_signed_in_user(monkeypatch, redis):
    from fastapi.testclient import TestClient

    from app import auth
    from app.initialized import fastapi_app
    virtual_machine.store_warnings(["The connector CS could not be listed (x)."])
    fastapi_app.dependency_overrides[auth.verify_token] = lambda: {}
    try:
        answer = TestClient(fastapi_app).get("/api/v1/virtualmachines/warnings")
    finally:
        fastapi_app.dependency_overrides.clear()
    assert answer.status_code == 200 and answer.json() == {"warnings": ["The connector CS could not be listed (x)."]}
    # Without a token the route is closed like the others (and it is not taken for the id of a machine).
    assert TestClient(fastapi_app).get("/api/v1/virtualmachines/warnings").status_code in (401, 403)
