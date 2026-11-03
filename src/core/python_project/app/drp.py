"""Disaster recovery: restores the backed up disks of a VM into a new CloudStack VM.

The disks are extracted from the Borg repository, made standalone (the backing
file of a CloudStack disk is merged into it), and copied over the volumes of a
virtual machine that is created for the occasion, as the manual procedure does.
"""

import json
import os
import shutil
from pathlib import Path
from uuid import uuid4

from app import file_browser, notifier
from app.cloudstack import endpoint, provisioning
from app import drp_history
from app.file_browser import run
from app.initialized import celery_app

WORK_DIRECTORY = "restore/.drp"
MOUNT_ROOT = "/mnt"
IMAGE_NAME = "disk.qcow2"
# Folders of the backup storage that are not VM repositories.
NOT_REPOSITORIES = {"restore", "template"}


def list_repositories(storage_path: str) -> list[str]:
    root = Path(storage_path)
    if not root.is_dir():
        return []
    return sorted(
        directory.name for directory in root.iterdir()
        if directory.is_dir() and directory.name not in NOT_REPOSITORIES
        and not directory.name.startswith(".")
        and (directory / "config").is_file() and (directory / "data").is_dir())


def get_mounted_pool_ids() -> list[str]:
    """CloudStack primary storages are mounted by their identifier."""
    root = Path(MOUNT_ROOT)
    if not root.is_dir():
        return []
    return sorted(directory.name for directory in root.iterdir() if directory.is_dir())


def prepare_disk(storage_path: str, repository: str, archive: str, directory: Path) -> tuple[Path, int]:
    """Extracts an archive and returns a standalone qcow2 image with its virtual size in bytes."""
    image = file_browser.extract_image(storage_path, repository, archive, directory)

    info = json.loads(run(["qemu-img", "info", "--output=json", str(image)]))
    if "backing-filename" in info or info["format"] != "qcow2":
        # The conversion writes a second image, next to the extracted one: its size is the data of the whole chain
        # (the disk and its backing file). A standalone disk, like a Windows disk installed from an ISO, needs none.
        chain = json.loads(run(["qemu-img", "info", "--backing-chain", "--output=json", str(image)]))
        file_browser.check_free_space(directory, sum(int(item.get("actual-size", 0)) for item in chain))
        # The conversion follows the backing file, which is only read.
        standalone = directory / IMAGE_NAME
        run(["qemu-img", "convert", "-f", info["format"], "-O", "qcow2",
             str(image), str(standalone)])
        image.unlink()
        image = standalone
        info = json.loads(run(["qemu-img", "info", "--output=json", str(image)]))
    return image, info["virtual-size"]


def get_volume_file(pool_id: str, volume: dict) -> Path:
    """The file of a volume on the primary storage, which must be mounted here."""
    pool_directory = Path(MOUNT_ROOT) / pool_id
    if not pool_directory.is_dir():
        raise provisioning.CloudStackError(
            f"The primary storage {pool_id} of the new VM is not mounted in BackROLL ({pool_directory}).")

    volume_file = (pool_directory / volume["path"]).resolve()
    if volume_file.parent != pool_directory.resolve():
        raise provisioning.CloudStackError(
            f"Unexpected volume path {volume['path']}.")
    if not volume_file.is_file():
        raise provisioning.CloudStackError(
            f"The file of the volume {volume['name']} does not exist: {volume_file}.")
    return volume_file


def replace_volume(image: Path, volume_file: Path):
    temporary = volume_file.with_name(volume_file.name + ".tmp")
    try:
        shutil.copyfile(image, temporary)
        os.chmod(temporary, 0o644)
        # Atomic: the volume is never half written.
        os.replace(temporary, volume_file)
    finally:
        temporary.unlink(missing_ok=True)


def report(task, step: str):
    print(f"[DRP] {step}")
    task.update_state(state="PROGRESS", meta={"step": step})


@celery_app.task(name="Restore a VM to a new CloudStack VM", bind=True)
def restore_to_new_cloudstack_vm(self, request: dict):
    from app.routes import connectors

    directory = Path(request["storage_path"]) / WORK_DIRECTORY / str(uuid4())
    vm_id = None
    run_id = request.get("run_id")

    def progress(step: str):
        # The record of the steps is only a record: a database that fails must not stop the restore.
        try:
            report(self, step)
            if run_id:
                drp_history.add_step(run_id, step)
        except Exception as record_error:
            print(f"Unable to record the step “{step}”. {record_error}")

    if run_id:
        drp_history.start(run_id, self.request.id)
    try:
        connector = connectors.filter_connector_by_id(request["connector_id"])
        cs = endpoint.cloudstack_connector(connector)

        progress("Checking the storage of CloudStack")
        if not get_mounted_pool_ids():
            raise provisioning.CloudStackError(
                f"No primary storage is mounted in {MOUNT_ROOT}: the restored disks could not be copied.")

        images = []
        for index, archive in enumerate(request["disks"]):
            progress(f"Extracting the disk {index + 1}/{len(request['disks'])} ({archive})")
            images.append(prepare_disk(request["storage_path"], request["repository"],
                                       archive, directory / str(index)))

        root_size = provisioning.to_gib(images[0][1])
        progress(f"Creating the virtual machine {request['name']}")
        vm_id = provisioning.deploy_vm(
            cs, request["name"], request["zone_id"], request["service_offering_id"],
            request["template_id"], request.get("network_id"), request.get("ip_address"),
            root_size, request.get("domain_id"), request.get("account"))

        for index, (_, size) in enumerate(images[1:], start=1):
            progress(f"Creating the data disk {index}")
            provisioning.create_and_attach_data_disk(
                cs, vm_id, f"{request['name']}-data{index}", request["zone_id"],
                request["data_disk_offering_id"], provisioning.to_gib(size),
                request.get("domain_id"), request.get("account"))

        # The volumes exist on the storage once the virtual machine has started.
        progress("Stopping the virtual machine to replace its disks")
        provisioning.stop_vm(cs, vm_id)

        volumes = provisioning.list_volumes(cs, vm_id)
        if len(volumes) != len(images):
            raise provisioning.CloudStackError(
                f"The new VM has {len(volumes)} volumes for {len(images)} restored disks.")

        for index, (volume, (image, _)) in enumerate(zip(volumes, images)):
            progress(f"Copying the disk {index + 1}/{len(images)} to {volume['name']}")
            pool_id = provisioning.get_storage_pool_id(cs, volume)
            replace_volume(image, get_volume_file(pool_id, volume))

        if request.get("start_after", True):
            progress("Starting the restored virtual machine")
            provisioning.start_vm(cs, vm_id)

        result = {"vm_id": vm_id, "vm_name": request["name"],
                  "volumes": [volume["name"] for volume in volumes],
                  "started": bool(request.get("start_after", True))}
        # The machine is restored: what follows only tells about it, and must never undo it. A failure here sent
        # the task to the cleaning below, which deleted the machine that had just been restored.
        try:
            if run_id:
                drp_history.finish(run_id, "success", vm_id=vm_id)
            notifier.send(request.get("hook_id"), notifier.drp_finished_message(request, vm_id),
                          notifier.drp_finished_blocks(request, vm_id))
        except Exception as record_error:
            print(f"The restore is done but its end could not be recorded. {record_error}")
        return result
    except Exception as exception:
        failure = exception
        if vm_id and request.get("cleanup_on_failure"):
            # Only the machine this restore created.
            try:
                provisioning.destroy_vm(cs, vm_id)
                failure = RuntimeError(
                    f"{exception} The virtual machine {request['name']} ({vm_id}) that was created was deleted.")
                vm_id = None
            except Exception as cleanup_error:
                failure = RuntimeError(
                    f"{exception} The virtual machine {request['name']} ({vm_id}) was created and could not be deleted: {cleanup_error}")
        elif vm_id:
            # Kept for inspection: nothing is deleted in CloudStack automatically.
            failure = RuntimeError(
                f"{exception} The virtual machine {request['name']} ({vm_id}) was created in CloudStack and kept.")
        if run_id:
            drp_history.finish(run_id, "failed", vm_id=vm_id, error=str(failure))
        notifier.send(request.get("hook_id"), notifier.drp_failed_message(request, str(failure)),
                      notifier.drp_failed_blocks(request, str(failure)))
        if failure is exception:
            raise
        raise failure from exception
    finally:
        shutil.rmtree(directory, ignore_errors=True)
