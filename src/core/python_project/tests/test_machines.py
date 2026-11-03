"""The list of the machines used to decide that a repository belongs to a deleted machine.
It must refuse to answer at the slightest doubt. These tests need the libvirt module of the backend container."""

import os
import uuid

import pytest

os.environ.setdefault("JWT_SECRET", "x" * 40)

pytest.importorskip("libvirt")

from sqlalchemy.pool import StaticPool  # noqa: E402
from sqlmodel import Session, SQLModel, create_engine  # noqa: E402

from app import machines  # noqa: E402
from app.database import Connectors, Hosts, Pools  # noqa: E402


@pytest.fixture
def database(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(machines, "get_engine", lambda: engine)
    return engine


def populate(engine, hosts=1, connector=True):
    with Session(engine) as session:
        connector_row = Connectors(name="cloudstack", url="http://x/client/api", login="k", password="s") if connector else None
        if connector_row:
            session.add(connector_row)
            session.commit()
            session.refresh(connector_row)
        pool = Pools(name="production", connector_id=connector_row.id if connector_row else None)
        session.add(pool)
        session.commit()
        session.refresh(pool)
        for number in range(hosts):
            session.add(Hosts(hostname=f"kvm-{number}", ipaddress=f"10.0.0.{number + 1}", username="root",
                              ssh=True, pool_id=pool.id))
        session.commit()


def test_every_machine_of_every_source_is_listed(database, monkeypatch):
    populate(database, hosts=2)
    monkeypatch.setattr(machines, "list_kvm_names", lambda host: {f"vm-of-{host.hostname}"})
    monkeypatch.setattr(machines, "list_cloudstack_names", lambda connector: {"i-2-1-VM", "i-2-2-VM"})
    names, warnings = machines.list_machine_names()
    assert names == {"vm-of-kvm-0", "vm-of-kvm-1", "i-2-1-VM", "i-2-2-VM"}
    assert warnings == []


def test_an_error_of_cloudstack_is_a_warning_not_an_empty_list(database, monkeypatch):
    """The stopped machines only exist in the answer of CloudStack: without it they would look deleted."""
    populate(database)
    monkeypatch.setattr(machines, "list_kvm_names", lambda host: {"running-vm"})

    def fail(connector):
        raise TimeoutError("CloudStack does not answer")

    monkeypatch.setattr(machines, "list_cloudstack_names", fail)
    names, warnings = machines.list_machine_names()
    assert any("cloudstack" in warning and "does not answer" in warning for warning in warnings)


def test_an_unreachable_hypervisor_is_a_warning(database, monkeypatch):
    populate(database, connector=False)

    def fail(host):
        raise RuntimeError("unreachable")

    monkeypatch.setattr(machines, "list_kvm_names", fail)
    names, warnings = machines.list_machine_names()
    assert any("kvm-0" in warning for warning in warnings)
    assert any("not trusted" in warning for warning in warnings)


def test_nothing_configured_or_nothing_found_is_never_trusted(database, monkeypatch):
    assert any("not trusted" in warning for warning in machines.list_machine_names()[1])
    populate(database)
    monkeypatch.setattr(machines, "list_kvm_names", lambda host: set())
    monkeypatch.setattr(machines, "list_cloudstack_names", lambda connector: set())
    assert any("not trusted" in warning for warning in machines.list_machine_names()[1])


def test_the_machines_of_the_projects_and_all_the_pages_are_asked_to_cloudstack(monkeypatch):
    asked = []

    class FakeCloudStack:
        def listVirtualMachines(self, **parameters):
            asked.append(parameters)
            return [{"instancename": f"i-{len(asked)}-VM"}]

    monkeypatch.setattr(machines.endpoint, "cloudstack_connector", lambda connector: FakeCloudStack())
    names = machines.list_cloudstack_names(object())
    assert names == {"i-1-VM", "i-2-VM"}
    assert all(call["fetch_list"] is True and call["listall"] is True for call in asked)
    assert {call.get("projectid") for call in asked} == {None, machines.ALL_PROJECTS}
