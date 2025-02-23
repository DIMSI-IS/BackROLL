import re

from app import shell


# TODO ?
# def add_storage(virtual_machine):
#     pass


def add_disk_access_check(virtual_machine):
    for disk in virtual_machine["storage"]:
        available = False
        error = None

        try:
            permissions = shell.subprocess_run(
                f"ls -l {disk["source"]}").split()[0]

            if re.match("-rw.r..r..", permissions) is None:
                raise ValueError(
                    f"Permissions must be like rw*r**r**. Actual permissions are {permissions}.")

            available = True
        except Exception as exception:
            error = str(exception)

        disk["available"] = available
        disk["availabilityError"] = error


def check_disks_access(virtual_machine):
    add_disk_access_check(virtual_machine)

    unavailable_disks = list(
        filter(lambda disk: disk["availabilityError"] is not None,
               virtual_machine["storage"]))

    if len(unavailable_disks) > 0:
        report = "\n".join(
            map(lambda disk: f"- {disk["device"]} at {disk["source"]}: {disk["availabilityError"]}", unavailable_disks))
        raise ValueError(f"Some disks are unavailable:\n{report}")
