import os
import re
from pathlib import Path

from app import shell


# TODO ?
# def add_storage(virtual_machine):
#     pass


def add_disk_access_check(virtual_machine):
    for path in ["/var", "/var/lib", "/var/lib/libvirt", "/var/lib/libvirt/images"]:
        path = Path(path)
        print(f"{path=} {path.exists()=}, {path.is_file()=}, {path.is_dir()=}, {path.stat()=}")

    for disk in virtual_machine["storage"]:
        path = disk["source"]

        status = {}
        for key, mode in [
            ("exists", os.F_OK),
            ("readable", os.R_OK),
        ]:
            status[key] = os.access(path, mode)
        disk["status"] = status


def check_disks_access(virtual_machine):
    add_disk_access_check(virtual_machine)

    unavailable_disks = list(filter(
        lambda disk: not all(disk["status"].values()),
        virtual_machine["storage"]))

    if len(unavailable_disks) > 0:
        report = "\n".join(map(
            lambda disk: f"- {disk["device"]} at {disk["source"]}: {
                ", ".join(map(lambda keyValue: f"{keyValue[0]}={keyValue[1]}", disk["status"].items()))}",
            unavailable_disks))
        raise ValueError(f"Some disks are unavailable:\n{report}")
