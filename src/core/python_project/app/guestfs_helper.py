"""Reads a VM disk image without mounting it on the host, thanks to libguestfs.

Runs as a separate process with the system Python, which provides the guestfs
module, not the virtual environment of the application. It reads one JSON
request per line on the standard input and answers one JSON line per request.
It imports nothing from the application.

Requests: {"id": 1, "op": "<name>", ...}
Answers:  {"id": 1, "ok": true, "result": ...} or {"id": 1, "ok": false, "error": "..."}
"""

import json
import os
import stat
import sys

import guestfs

# The image is only ever opened read-only.
SKIPPED_FILESYSTEMS = {"swap", "unknown", "LVM2_member", "crypto_LUKS"}


def make_handle(images: list[str]):
    g = guestfs.GuestFS(python_return_dict=True)
    if not os.path.exists("/dev/kvm"):
        # Without hardware acceleration, QEMU emulates the processor: slow but working.
        g.set_backend_setting("force_tcg", "1")
    for image in images:
        g.add_drive_opts(image, readonly=1)
    g.launch()
    return g


def entry_type(mode: int) -> str:
    if stat.S_ISDIR(mode):
        return "directory"
    if stat.S_ISLNK(mode):
        return "link"
    if stat.S_ISREG(mode):
        return "file"
    return "other"


class Session:
    def __init__(self, images: list[str]):
        self.g = make_handle(images)
        self.mounted = False

    def filesystems(self):
        filesystems = self.g.list_filesystems()
        return [{"device": device, "type": kind}
                for device, kind in sorted(filesystems.items())
                if kind not in SKIPPED_FILESYSTEMS]

    def mount(self, device=None):
        """Mounts the given filesystem, or the operating system found in the image."""
        if self.mounted:
            self.g.umount_all()
            self.mounted = False

        if device is None:
            roots = self.g.inspect_os()
            if not roots:
                raise RuntimeError(
                    "No operating system found. Choose a filesystem.")
            root = roots[0]
            mountpoints = self.g.inspect_get_mountpoints(root)
            # Shortest first: / must be mounted before /boot.
            for mountpoint, dev in sorted(mountpoints.items(), key=lambda item: len(item[0])):
                try:
                    self.g.mount_ro(dev, mountpoint)
                except RuntimeError:
                    # A broken secondary mount must not prevent the browsing.
                    if mountpoint == "/":
                        raise
        else:
            self.g.mount_ro(device, "/")
        self.mounted = True
        return {"mounted": device or "operating system"}

    def ls(self, path):
        if not self.g.is_dir(path):
            raise RuntimeError("Not a directory.")

        names = sorted(self.g.ls(path), key=str.lower)
        entries = []
        if names:
            stats = self.g.lstatnslist(path, names)
            for name, info in zip(names, stats):
                entries.append({
                    "name": name,
                    "type": entry_type(info["st_mode"]),
                    "size": info["st_size"],
                    "mode": oct(stat.S_IMODE(info["st_mode"])),
                    "modified": info["st_mtime_sec"],
                })
        entries.sort(key=lambda entry: (entry["type"] != "directory", entry["name"].lower()))
        return entries

    def stat(self, path):
        info = self.g.lstatns(path)
        return {"type": entry_type(info["st_mode"]), "size": info["st_size"]}

    def download(self, path, destination):
        """Copies a file, or a directory as a tar archive, out of the image."""
        if self.g.is_dir(path):
            self.g.tar_out(path, destination)
            return {"type": "directory"}
        self.g.download(path, destination)
        return {"type": "file"}

    def close(self):
        try:
            self.g.shutdown()
        finally:
            self.g.close()


def main():
    session = None
    for line in sys.stdin:
        request = json.loads(line)
        try:
            operation = request["op"]
            if operation == "open":
                # One image, or all the disks of a virtual machine, which may be mounted together.
                session = Session(request["images"] if "images" in request else [request["image"]])
                result = {"filesystems": session.filesystems()}
            elif operation == "mount":
                result = session.mount(request.get("device"))
            elif operation == "ls":
                result = session.ls(request["path"])
            elif operation == "stat":
                result = session.stat(request["path"])
            elif operation == "download":
                result = session.download(request["path"], request["destination"])
            elif operation == "close":
                if session:
                    session.close()
                print(json.dumps({"id": request["id"], "ok": True, "result": None}), flush=True)
                return
            else:
                raise RuntimeError(f"Unknown operation {operation}.")
            print(json.dumps({"id": request["id"], "ok": True, "result": result}), flush=True)
        except Exception as exception:
            print(json.dumps({"id": request.get("id"), "ok": False,
                              "error": str(exception)}), flush=True)


if __name__ == "__main__":
    main()
