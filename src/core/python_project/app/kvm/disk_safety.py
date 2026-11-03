"""Rules that keep the disks of a running machine safe while it is backed up.

A backup puts the machine on an overlay file ("<disk>.snap"), copies the disk below it, then commits the overlay
back into the disk (block commit) and pivots the machine onto the disk again. Everything that can go wrong
between the snapshot and the pivot leaves the machine WRITING in the overlay: that file is then the only copy of
the recent writes of the machine, and it must never be deleted.

The rules here:
 - an overlay is never deleted, nor moved, while the XML of the machine lists it or a process holds it open;
 - a commit is never cancelled: when it can not be finished the machine is left alone and an operator is told;
 - the pivot is asked when the commit has copied everything, and tried again until libvirt says it is ready;
 - after the pivot the XML is read again: the disk must be back on its base file;
 - nothing is repaired by itself before a backup: an overlay already in use stops the backup.

The functions take the libvirt domain (or an object that looks like it), so that they can be tested without KVM.
"""

import shlex
import time
import xml.etree.ElementTree as ET

try:
    import libvirt
except ImportError:  # a machine without the libvirt library: only the tests of the pure functions run there
    libvirt = None

LibvirtError = libvirt.libvirtError if libvirt else Exception

# The values of libvirt, with the numbers it documents when the library is not there.
COMMIT_ACTIVE = getattr(libvirt, "VIR_DOMAIN_BLOCK_COMMIT_ACTIVE", 4)
COMMIT_DELETE = getattr(libvirt, "VIR_DOMAIN_BLOCK_COMMIT_DELETE", 2)
ABORT_PIVOT = getattr(libvirt, "VIR_DOMAIN_BLOCK_JOB_ABORT_PIVOT", 2)
ERR_BLOCK_COPY_ACTIVE = getattr(libvirt, "VIR_ERR_BLOCK_COPY_ACTIVE", 83)

# The commit of a big disk takes hours: this is only the end of a job that does not move at all.
COMMIT_TIMEOUT_SECONDS = 6 * 3600
POLL_SECONDS = 2
PIVOT_CHECKS = 15


class BackupStateError(Exception):
    """The state of a disk is not the one that a backup needs. Nothing was changed to "fix" it."""


# -- the XML of the machine -------------------------------------------------------------------------------

def overlay_of(source: str) -> str:
    """The overlay of a disk file, named like the snapshot XML names it."""
    return f"{base_of(source)}.snap"


def base_of(source: str) -> str:
    return source.replace(".snap", "")


def disk_chain(dom, target: str) -> list[str]:
    """[the file the machine writes to, its backing file, ...] of one disk, read in the XML of the machine."""
    root = ET.fromstring(dom.XMLDesc(0))
    for disk in root.findall("./devices/disk"):
        name = disk.find("target")
        if name is not None and name.get("dev") == target:
            chain, node = [], disk
            while node is not None:
                source = node.find("source")
                if source is None or not source.get("file"):
                    break
                chain.append(source.get("file"))
                node = node.find("backingStore")
            return chain
    raise BackupStateError(f"{target}: the disk is not in the XML of the machine")


def files_in_use(dom) -> set[str]:
    """Every file of every disk of the machine: all of them are open in QEMU."""
    root = ET.fromstring(dom.XMLDesc(0))
    used = set()
    for source in root.iter("source"):
        if source.get("file"):
            used.add(source.get("file"))
    return used


def job_active(dom, target: str) -> bool:
    return bool(dom.blockJobInfo(target, 0))


# -- before the backup -----------------------------------------------------------------------------------------

def preflight(dom, target: str) -> str:
    """Refuses a disk that is not on its base file with no job on it. Returns the path of the base file."""
    try:
        top = disk_chain(dom, target)[0]
        if ".snap" in top:
            raise BackupStateError(f"{target}: the machine already writes in an overlay ({top})")
        if job_active(dom, target):
            raise BackupStateError(f"{target}: a block job is already running on this disk")
    except BackupStateError:
        raise
    except LibvirtError as error:
        raise BackupStateError(f"{target}: libvirt could not be asked ({error})") from error
    return top


# -- the commit and the pivot --------------------------------------------------------------------------------

def _not_ready(error) -> bool:
    code = error.get_error_code() if hasattr(error, "get_error_code") else None
    return code == ERR_BLOCK_COPY_ACTIVE or "not ready" in str(error).lower()


def commit_and_pivot(dom, target: str, base: str, overlay: str, timeout: float = COMMIT_TIMEOUT_SECONDS,
                     sleep=time.sleep, clock=time.monotonic):
    """Commits the overlay into the base file and puts the machine back on the base file.

    Returns when the XML shows the base file as the file of the disk, and raises BackupStateError when it could
    not be checked. A commit that takes too long is left running: cancelling it would leave the machine on
    the overlay."""
    try:
        if disk_chain(dom, target)[0] == base:
            return  # already on the base file: nothing to commit
        if job_active(dom, target):
            raise BackupStateError(f"{target}: a block job is already running, it is left alone")
        dom.blockCommit(target, base, overlay, 0, COMMIT_ACTIVE | COMMIT_DELETE)

        deadline = clock() + timeout
        while True:
            info = dom.blockJobInfo(target, 0)
            if not info:
                # No job any more: either the pivot is done, or the job was cancelled by something else.
                if disk_chain(dom, target)[0] == base:
                    return
                raise BackupStateError(f"{target}: the commit job disappeared and the machine is still on {overlay}")
            if info.get("end", 0) > 0 and info.get("cur", 0) >= info["end"]:
                try:
                    dom.blockJobAbort(target, ABORT_PIVOT)
                    break
                except LibvirtError as error:
                    # The job copies the writes that come while it ends: it is ready a little later.
                    if not _not_ready(error):
                        raise
            if clock() > deadline:
                raise BackupStateError(f"{target}: the commit did not end in time, the job is left running")
            sleep(POLL_SECONDS)

        for _ in range(PIVOT_CHECKS):
            if disk_chain(dom, target)[0] == base:
                return
            sleep(1)
        raise BackupStateError(f"{target}: the pivot is not confirmed, the XML still shows {disk_chain(dom, target)[0]}")
    except BackupStateError:
        raise
    except LibvirtError as error:
        raise BackupStateError(f"{target}: libvirt refused or lost the commit ({error})") from error


def recover_disks(dom, disks: list[dict], on_attention, **options) -> list[str]:
    """After a failed backup: brings back on their base file the disks that are on an overlay.

    A disk that can not be recovered is reported with on_attention(device, message) and left as it is.
    Returns the devices that need attention."""
    failed = []
    for disk in disks:
        device = disk["device"]
        try:
            base = base_of(disk["source"])
            if disk_chain(dom, device)[0] == base:
                continue
            commit_and_pivot(dom, device, base, overlay_of(disk["source"]), **options)
        except (BackupStateError, LibvirtError) as error:
            failed.append(device)
            on_attention(device, str(error))
    return failed


# -- the cleaning ------------------------------------------------------------------------------------------------

def trash_name(path: str, now: float | None = None) -> str:
    return f"{path}.trash-{int(time.time() if now is None else now)}"


def safe_remove(dom, path: str, run_on_hypervisor) -> str:
    """Puts a leftover overlay aside (renamed, not deleted) when nothing uses it. Returns the new name.

    run_on_hypervisor(command) -> {"rc": int, ...} runs on the machine that hosts the VM: a file deleted from
    another client of the NFS share disappears under the process that holds it (stale file handle)."""
    if path in files_in_use(dom):
        raise BackupStateError(f"{path} is in the XML of the machine, it is in use")
    quoted = shlex.quote(path)
    # fuser answers 0 when a process holds the file, 1 when none does. Anything else means it could not tell.
    answer = run_on_hypervisor(f"fuser {quoted}")
    if answer["rc"] == 0:
        raise BackupStateError(f"{path} is open by a process")
    if answer["rc"] != 1:
        raise BackupStateError(f"{path}: it could not be checked that nobody uses it")
    target = trash_name(path)
    moved = run_on_hypervisor(f"mv -n {quoted} {shlex.quote(target)}")
    if moved["rc"] != 0:
        raise BackupStateError(f"{path} could not be put aside")
    return target
