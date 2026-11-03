"""A tiny fake CloudStack API, to try the disaster recovery without a real CloudStack.

    python tests/fake_cloudstack.py /mnt/fake-pool 8099

Add a connector whose URL is http://localhost:8099/client/api (run it in the same
container as the worker). The volumes are real qcow2 files in the given
directory, which plays the role of a primary storage: it must be a folder of /mnt.
"""

import itertools
import json
import subprocess
import sys
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

POOL = Path(sys.argv[1])
PORT = int(sys.argv[2])
POOL_ID = POOL.name
ZONE = {"id": str(uuid.uuid4()), "name": "Fake zone"}
DOMAIN = {"id": str(uuid.uuid4())}
SUBDOMAIN = {"id": str(uuid.uuid4())}
OFFERING = {"id": str(uuid.uuid4()), "name": "Small", "cpunumber": 2, "memory": 2048}
TEMPLATE = {"id": str(uuid.uuid4()), "name": "Fake Ubuntu", "zoneid": ZONE["id"], "size": 1}
NETWORK = {"id": str(uuid.uuid4()), "name": "Fake network", "zoneid": ZONE["id"], "cidr": "10.0.0.0/24"}
DISK_OFFERING = {"id": str(uuid.uuid4()), "name": "Custom", "iscustomized": True}

volumes = []
jobs = {}
counter = itertools.count()


def add_volume(name, vm_id, volume_type):
    path = str(uuid.uuid4())
    # What CloudStack creates: an empty disk, unrelated to the backup.
    subprocess.run(["qemu-img", "create", "-f", "qcow2", str(POOL / path), "1M"], check=True,
                   capture_output=True)
    volume = {"id": str(uuid.uuid4()), "name": name, "path": path, "storageid": POOL_ID,
              "virtualmachineid": vm_id, "type": volume_type, "deviceid": len(volumes)}
    volumes.append(volume)
    return volume


def job(result=None):
    identifier = str(next(counter))
    jobs[identifier] = result or {}
    return {"jobid": identifier}


def handle(command, parameters):
    if command == "listZones":
        return {"zone": [ZONE]}
    if command == "listDomains":
        return {"domain": [{"id": DOMAIN["id"], "name": "ROOT", "path": "ROOT"},
                           {"id": SUBDOMAIN["id"], "name": "portugal", "path": "ROOT/IAAS/portugal"}]}
    if command == "listAccounts":
        return {"account": [{"id": str(uuid.uuid4()), "name": "portugal-admin", "state": "enabled"}]}
    if command == "listServiceOfferings":
        return {"serviceoffering": [OFFERING]}
    if command == "listTemplates":
        return {"template": [TEMPLATE]}
    if command == "listNetworks":
        return {"network": [NETWORK]}
    if command == "listDiskOfferings":
        return {"diskoffering": [DISK_OFFERING]}
    if command == "deployVirtualMachine":
        vm_id = str(uuid.uuid4())
        add_volume("ROOT-fake", vm_id, "ROOT")
        print("deploy", parameters, flush=True)
        return job({"virtualmachine": {"id": vm_id, "name": parameters["name"]}})
    if command == "createVolume":
        return job({"volume": add_volume(parameters["name"], None, "DATADISK")})
    if command == "attachVolume":
        for volume in volumes:
            if volume["id"] == parameters["id"]:
                volume["virtualmachineid"] = parameters["virtualmachineid"]
        return job()
    if command == "destroyVirtualMachine":
        for volume in [v for v in volumes if v["virtualmachineid"] == parameters["id"]]:
            (POOL / volume["path"]).unlink(missing_ok=True)
            volumes.remove(volume)
        return job()
    if command in ("stopVirtualMachine", "startVirtualMachine"):
        print(command, flush=True)
        return job()
    if command == "queryAsyncJobResult":
        return {"jobstatus": 1, "jobresult": jobs[parameters["jobid"]]}
    if command == "listVolumes":
        return {"volume": [v for v in volumes if v["virtualmachineid"] == parameters["virtualmachineid"]]}
    if command == "listStoragePools":
        return {"storagepool": [{"id": POOL_ID, "name": "Fake pool"}]}
    return {"errorcode": 530, "errortext": f"Unknown command {command}"}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        parameters = {key: values[0] for key, values in query.items()}
        command = parameters.get("command", "")
        body = json.dumps({f"{command.lower()}response": handle(command, parameters)}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length).decode()
        self.path = f"{self.path}{'&' if '?' in self.path else '?'}{body}"
        self.do_GET()

    def log_message(self, *arguments):
        pass


if __name__ == "__main__":
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
