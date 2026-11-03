"""The restore of a disk extracts it on the disk of BackROLL before it replaces the disk of the machine.
Without room, the machine is left alone: it is not stopped and nothing is written."""

import shutil

import pytest

pytest.importorskip("libvirt")

from app import file_browser, restore  # noqa: E402

VM = {"name": "i-1-VM", "uuid": "vm-1", "host": "host-1", "pool_id": "pool-1", "cloudstack_instance": True}


def test_a_restore_that_would_fill_the_disk_stops_before_the_machine_is_touched(monkeypatch, tmp_path):
    commands = []
    monkeypatch.setattr(restore.storage, "retrieveStoragePathFromHostBackupPolicy", lambda info: {"path": str(tmp_path)})
    monkeypatch.setattr(restore.shell, "subprocess_run", lambda command: commands.append(command) or "")
    monkeypatch.setattr(restore.shell, "subprocess_popen", lambda command: commands.append(command) or "")
    monkeypatch.setattr(restore.shell, "os_system", lambda command: commands.append(command))
    monkeypatch.setattr(restore.os, "chdir", lambda path: None)
    monkeypatch.setattr(file_browser, "archive_size", lambda *arguments: 12 * 1024 ** 3)
    monkeypatch.setattr(shutil, "disk_usage", lambda path: type("U", (), {"free": 5 * 1024 ** 3})())
    stopped = []
    monkeypatch.setattr(restore.cs_vm_command, "stop_vm", lambda *arguments: stopped.append(arguments))
    monkeypatch.setattr(restore.kvm_manage_vm, "stop_vm", lambda *arguments: stopped.append(arguments))

    with pytest.raises(file_browser.NotEnoughSpace, match="Not enough free space"):
        restore.restore_task(None, VM, {"pool_id": "pool-1"}, [{"device": "hda", "source": "/mnt/p/disk"}], "hda_disk_1")

    assert stopped == []
    assert not any("borg extract" in command for command in commands)
    assert not any(command.startswith("cp ") or command.startswith("mv ") for command in commands)
