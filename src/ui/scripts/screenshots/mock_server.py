"""Demo mock of the BackROLL API, used only to take documentation screenshots.

It serves the built UI (a `dist` folder, with the single page application fallback) and answers
the `/api/v1/...` routes with fictional data. Nothing here talks to a real backend.

    python mock_server.py <dist folder> [--port 8099]

Demo credentials (fictional): user "admin", password "demo-admin-pass".
"""
import argparse
import json
import os
import mimetypes
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response

DEMO_USER = "admin"
DEMO_PASSWORD = "demo-admin-pass"
# No version in the pictures of the documentation: they would have to be taken again at each release.
VERSION = ""

for _ext, _type in ((".js", "text/javascript"), (".css", "text/css"), (".svg", "image/svg+xml"),
                    (".woff2", "font/woff2"), (".woff", "font/woff"), (".json", "application/json")):
    mimetypes.add_type(_type, _ext)


def vm_uuid(name: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{name}.demo.example.com"))


def disk_uuid(name: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"disk.{name}.demo.example.com"))


def rid(kind: str, number: int) -> str:
    """Identifier of a resource: the API gives strings."""
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{kind}.{number}.demo.example.com"))


def iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


NOW = datetime.now()
STORAGE_TOTAL = 1024 ** 4  # 1 TiB
STORAGE_USED = 340 * 1024 ** 3

STORAGE = [{
    "id": rid("storage", 1), "name": "backup_storage", "path": "/mnt/backup_storage",
    "info": {"total": STORAGE_TOTAL, "used": STORAGE_USED, "free": STORAGE_TOTAL - STORAGE_USED},
}]
CONNECTORS = [{"id": rid("connector", 1), "name": "cloudstack-lab", "url": "https://cloudstack.example.com/client/api",
               "login": "demo-api-user"}]
HOOKS = [{"id": rid("hook", 1), "name": "slack-notifications",
          "value": "https://hooks.slack.com/…real"}]  # masked, like the real API: the address is a secret
POLICIES = [
    {"id": rid("policy", 1), "name": "daily-backup", "description": "Daily backup of the production machines",
     "schedule": "0 2 * * *", "storage": rid("storage", 1), "externalhook": rid("hook", 1), "enabled": True,
     "retention_day": 7, "retention_week": 4, "retention_month": 6, "retention_year": 1,
     "file_paths": "/etc\n/var/www"},
    {"id": rid("policy", 2), "name": "weekly-archive", "description": "Weekly archive of the staging machines",
     "schedule": "0 3 * * 0", "storage": rid("storage", 1), "externalhook": None, "enabled": False,
     "retention_day": 0, "retention_week": 8, "retention_month": 12, "retention_year": 2,
     "file_paths": ""},
]
POOLS = [
    {"id": rid("pool", 1), "name": "production", "policy_id": rid("policy", 1), "connector_id": rid("connector", 1)},
    {"id": rid("pool", 2), "name": "staging", "policy_id": rid("policy", 2), "connector_id": rid("connector", 1)},
]
HOSTS = [
    {"id": rid("host", 1), "hostname": "kvm-01", "pool_id": rid("pool", 1), "ipaddress": "10.0.0.11", "ssh": True,
     "tags": "kvm", "state": "Reachable"},
    {"id": rid("host", 2), "hostname": "kvm-02", "pool_id": rid("pool", 2), "ipaddress": "10.0.0.12", "ssh": True,
     "tags": "kvm", "state": "Reachable"},
]
# name, cpus, memory (KiB), host id, state
VM_SPECS = [
    ("web-01", 2, 4 * 1024 * 1024, 1, "Running"),
    ("web-02", 2, 4 * 1024 * 1024, 1, "Running"),
    ("db-01", 4, 8 * 1024 * 1024, 1, "Running"),
    ("mail-01", 2, 4 * 1024 * 1024, 1, "Running"),
    ("files-01", 2, 2 * 1024 * 1024, 1, "Running"),
    ("app-01", 4, 8 * 1024 * 1024, 2, "Running"),
    # Never backed up and not running: it must stay in the list of the machines at risk, marked as not running.
    ("old-test", 1, 1024 * 1024, 2, "Shutoff"),
]
VMS = [{"id": 10 + index, "uuid": vm_uuid(name), "name": name, "cpus": cpus, "mem": mem, "host": HOSTS[host - 1]["id"],
        "host_tag": "kvm", "state": state, "pool_id": HOSTS[host - 1]["pool_id"]}
       for index, (name, cpus, mem, host, state) in enumerate(VM_SPECS)]
VM_BY_UUID = {vm["uuid"]: vm for vm in VMS}

# Last backup of each machine, in days before now. None: never backed up.
LAST_BACKUP_DAYS = {"web-01": 0.3, "web-02": 0.3, "db-01": 0.3, "mail-01": 5, "files-01": 0.3, "app-01": None}


def backup_archives(vm: dict) -> list:
    """Archives of a machine: one disk archive and two file archives per day."""
    last = LAST_BACKUP_DAYS.get(vm["name"])
    if last is None:
        return []
    base = NOW.replace(hour=2, minute=0, second=0, microsecond=0)
    archives = []
    shift = (1 if base > NOW else 0) + (int(last) if last >= 1 else 0)
    for day in range(7):
        moment = base - timedelta(days=day + shift)
        epoch = int(moment.timestamp())
        for offset, name in ((0, f"vda_{disk_uuid(vm['name'])}_{epoch}"),
                             (180, f"files_etc_{epoch + 180}"),
                             (240, f"files_var-www_{epoch + 240}")):
            start = moment + timedelta(seconds=offset)
            archives.append({"name": name, "start": iso(start), "archive": name})
    return archives


def browser_zone():
    """The time zone of the browser that displays the demo: the page shows the tasks of ITS today."""
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(os.environ.get("MOCK_TIMEZONE", "Europe/Paris"))
    except Exception:  # no time zone database on this machine
        return timezone.utc


def tasks_backup(now: datetime | None = None) -> list:
    """Backup tasks of today (in the time zone of the browser), `started` and `received` in seconds.

    The page lists the tasks of one day: shortly after midnight, tasks put "a few hours ago" or "10 minutes ago"
    would belong to yesterday and the page would show none. They are all kept between midnight and now."""
    moment = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    local = moment.astimezone(browser_zone())
    midnight = local.replace(hour=0, minute=0, second=0, microsecond=0)
    span = max(1.0, min((local - midnight).total_seconds() - 2, 6 * 3600))
    # (machine, state, fraction of the span ago, runtime in seconds)
    plan = [("web-01", "SUCCESS", 0.95, 412), ("web-02", "SUCCESS", 0.85, 388),
            ("db-01", "SUCCESS", 0.7, 1260), ("mail-01", "FAILURE", 0.55, 37),
            ("files-01", "SUCCESS", 0.4, 905), ("web-01", "SUCCESS", 0.25, 96),
            ("files-01", "STARTED", 0.04, None), ("db-01", "RECEIVED", 0.01, None),
            # A machine that is off: Celery says success, but nothing was copied.
            ("web-02", "SKIPPED", 0.3, 0)]
    items = []
    for machine, state, fraction, runtime in plan:
        started = moment.timestamp() - span * fraction
        vm = next(v for v in VMS if v["name"] == machine)
        items.append({
            "uuid": str(uuid.uuid5(uuid.NAMESPACE_DNS, f"task.{machine}.{fraction}")),
            "name": "Single_VM_Backup", "state": state,
            "args": [{"name": machine, "uuid": vm["uuid"]}],
            "received": started - 2, "started": started if state != "RECEIVED" else None,
            "runtime": runtime, "ip_address": "10.0.0.5",
            "reason": "The virtual machine is not running (state Stopped): it is not backed up."
            if state == "SKIPPED" else None,
        })
    return items


def repositories() -> list:
    result = []
    for vm in VMS:
        days = LAST_BACKUP_DAYS.get(vm["name"])
        result.append({"name": vm["name"], "state": "ok",
                       "last_backup": iso(NOW - timedelta(days=days)) if days is not None else None,
                       "age_days": days})
    return result


def audit_items() -> list:
    entries = [
        ("admin", "login", "Login of admin", 200, "10.0.0.50"),
        ("admin", "policy.update", "Policy daily-backup updated", 200, "10.0.0.50"),
        ("operator", "backup.start", "Backup started for web-01", 200, "10.0.0.51"),
        ("operator", "backup.start", "Backup started for db-01", 200, "10.0.0.51"),
        (None, "login", "Login failed for user guest", 401, "192.0.2.44"),
        ("admin", "host.connect", "SSH key installed on kvm-02", 200, "10.0.0.50"),
        ("admin", "user.create", "User auditor created with role viewer", 200, "10.0.0.50"),
        ("operator", "backup.files.browse", "Files of web-01 files_etc browsed", 200, "10.0.0.51"),
        ("admin", "drp.restore", "Disaster recovery of web-01 on cloudstack-lab", 200, "10.0.0.50"),
        ("operator", "backup.delete", "Backup vda of mail-01 removed", 403, "10.0.0.51"),
        ("auditor", "login", "Login of auditor", 200, "10.0.0.52"),
        ("alice", "login", "role=admin from BackROLL-Admins", 200, "10.0.0.60", "ad"),
        ("frank", "login", "refused: the user is in none of the groups that give access", 401, "10.0.0.61", "ad"),
        ("alice", "directory.update", "Active Directory settings changed: timeout_seconds", 200, "10.0.0.60", "ad"),
    ]
    items = []
    for index, (user, action, detail, status, ip, *more) in enumerate(entries):
        items.append({"id": index + 1, "created_at": iso(NOW - timedelta(minutes=17 * (index + 1))),
                      "username": user, "action": action, "detail": detail, "status_code": status,
                      "ip_address": ip, "source": more[0] if more else "local"})
    return items


USERS = [
    {"id": 1, "name": "admin", "role": "admin", "is_active": True, "locked": False,
     "created_at": iso(NOW - timedelta(days=90))},
    {"id": 2, "name": "operator", "role": "editor", "is_active": True, "locked": False,
     "created_at": iso(NOW - timedelta(days=60))},
    {"id": 3, "name": "auditor", "role": "viewer", "is_active": True, "locked": False,
     "created_at": iso(NOW - timedelta(days=30))},
    {"id": 4, "name": "intern", "role": "viewer", "is_active": False, "locked": False,
     "created_at": iso(NOW - timedelta(days=12))},
    {"id": 5, "name": "alice", "role": "admin", "is_active": True, "locked": False, "auth_source": "ad",
     "display_name": "Alice Martin", "email": "alice@corp.local", "created_at": iso(NOW - timedelta(days=8))},
    {"id": 6, "name": "bob", "role": "editor", "is_active": True, "locked": False, "auth_source": "ad",
     "display_name": "Bob Durand", "email": "bob@corp.local", "created_at": iso(NOW - timedelta(days=3))},
]
for _user in USERS:
    _user.setdefault("auth_source", "local")

DRP_HISTORY = [
    {"id": 3, "created_at": iso(NOW - timedelta(days=2, hours=3)), "username": "admin",
     "repository": "web-01", "connector_name": "cloudstack-lab", "domain_name": "ROOT", "account": "demo",
     "vm_name": "web-01-restored", "status": "success",
     "finished_at": iso(NOW - timedelta(days=2, hours=3) + timedelta(minutes=9, seconds=24)),
     "vm_id": "3f1c2a9e-0000-4000-8000-00000000d3a1", "error": None, "disks": ["vda"],
     "log": "Reading the backup\nExtracting vda\nCreating the volume\nCreating the virtual machine\nStarting the machine"},
    {"id": 2, "created_at": iso(NOW - timedelta(days=9)), "username": "operator",
     "repository": "db-01", "connector_name": "cloudstack-lab", "domain_name": "ROOT", "account": "demo",
     "vm_name": "db-01-restored", "status": "failed",
     "finished_at": iso(NOW - timedelta(days=9) + timedelta(minutes=2, seconds=5)),
     "vm_id": None, "error": "No primary storage is available in the zone", "disks": ["vda"],
     "log": "Reading the backup\nExtracting vda\nCreating the volume"},
    {"id": 1, "created_at": iso(NOW - timedelta(days=21)), "username": "admin",
     "repository": "mail-01", "connector_name": "cloudstack-lab", "domain_name": None, "account": None,
     "vm_name": "mail-01-restored", "status": "success",
     "finished_at": iso(NOW - timedelta(days=21) + timedelta(minutes=12, seconds=40)),
     "vm_id": "3f1c2a9e-0000-4000-8000-00000000d3a2", "error": None, "disks": ["vda"],
     "log": "Reading the backup\nExtracting vda\nCreating the volume\nCreating the virtual machine"},
]

CLOUDSTACK_OPTIONS = {
    "domains": [{"id": "d-root", "path": "ROOT"}],
    "zones": [{"id": "zone-1", "name": "zone-lab"}],
    "service_offerings": [{"id": "so-1", "name": "Small Instance", "cpus": 1, "memory": 2048},
                          {"id": "so-2", "name": "Medium Instance", "cpus": 2, "memory": 4096},
                          {"id": "so-3", "name": "Large Instance", "cpus": 4, "memory": 8192}],
    "templates": [{"id": "tpl-1", "name": "debian-12-template", "zone_id": "zone-1"},
                  {"id": "tpl-2", "name": "ubuntu-22-04-template", "zone_id": "zone-1"}],
    "networks": [{"id": "net-1", "name": "demo-network", "cidr": "10.0.0.0/24", "zone_id": "zone-1"}],
    "disk_offerings": [{"id": "do-1", "name": "Custom disk", "custom": True}],
    "mounted_pools": ["primary-01"],
}

JOBS = [
    {"name": "Backup (VM)", "mode": "single", "type": "backup"},
    {"name": "Backup (Pool)", "mode": "pool", "type": "backup"},
    {"name": "Disk Restore & Replace (VM)", "mode": "single", "type": "restore"},
]


def entry(name, kind="file", size=0, days=3):
    jitter = sum(ord(c) for c in name)
    moment = NOW - timedelta(days=days, hours=jitter % 19, minutes=jitter % 53)
    return {"name": name, "type": kind, "size": size, "modified": int(moment.timestamp())}


FILESYSTEM = {
    "/": [entry("etc", "directory"), entry("var", "directory")],
    "/etc": [entry("cron.d", "directory", days=40), entry("nginx", "directory", days=5),
             entry("ssh", "directory", days=40), entry("fstab", size=742, days=40),
             entry("hostname", size=7, days=40), entry("hosts", size=221, days=40),
             entry("os-release", size=267, days=40), entry("resolv.conf", size=78, days=1)],
    "/etc/nginx": [entry("conf.d", "directory", days=5), entry("sites-available", "directory", days=5),
                   entry("sites-enabled", "directory", days=5), entry("snippets", "directory", days=40),
                   entry("fastcgi_params", size=1007, days=40), entry("mime.types", size=5349, days=40),
                   entry("nginx.conf", size=1490, days=5), entry("proxy_params", size=441, days=40)],
    "/var": [entry("www", "directory", days=5)],
    "/var/www": [entry("html", "directory", days=2)],
    "/var/www/html": [entry("assets", "directory", days=2), entry("css", "directory", days=2),
                      entry("js", "directory", days=2), entry("404.html", size=1832, days=30),
                      entry("favicon.ico", size=15086, days=30), entry("index.html", size=11264, days=2),
                      entry("robots.txt", size=64, days=30)],
}

# ---------------------------------------------------------------------------------------------

app = FastAPI(title="BackROLL demo mock")
RESULTS: dict = {}  # task id -> response of the status route
API = "/api/v1"
DIST: Path = Path(".")


def asynchronous(info) -> dict:
    """Stores a result and answers like the real API does for the lists: a status location."""
    task_id = str(uuid.uuid4())
    RESULTS[task_id] = {"state": "SUCCESS", "info": info}
    return {"Location": f"{API}/status/{task_id}", "state": "PENDING"}


@app.get(f"{API}/status/{{task_id}}")
def status(task_id: str):
    return RESULTS.get(task_id, {"state": "FAILURE", "status": "unknown task"})


@app.get(f"{API}/auth/setup")
def setup():
    return {"required": False}


@app.post(f"{API}/auth/password/login")
async def login(request: Request):
    body = await request.json()
    if body.get("username") != DEMO_USER or body.get("password") != DEMO_PASSWORD:
        raise HTTPException(status_code=401, detail="Bad credentials")
    return {"access_token": "demo-token", "token_type": "bearer", "expires_in": 8 * 3600,
            "user": {"id": 1, "name": "admin", "role": "admin"}}


@app.get(f"{API}/users")
def users():
    return USERS


@app.get(f"{API}/audit")
def audit(limit: int = 25, offset: int = 0, failed_only: bool = False, username: str = "", action: str = "",
          source: str = ""):
    items = [i for i in audit_items()
             if (not failed_only or i["status_code"] >= 400)
             and (not source or i["source"] == source)
             and (not username or i["username"] == username)
             and (not action or action in i["action"])]
    return {"items": items[offset:offset + limit], "total": len(items)}


# The Active Directory: what the page of its settings shows. The password of the service account is never given.
DIRECTORY = {
    "enabled": True, "server_url": "ldaps://dc01.corp.local:636", "start_tls": False, "verify_certificate": True,
    "ca_certificate": "", "base_dn": "DC=corp,DC=local", "bind_dn": "CN=svc-backroll,OU=Service,DC=corp,DC=local",
    "has_bind_password": True,
    "user_filter": "(&(objectCategory=person)(objectClass=user)(|(sAMAccountName={username})(userPrincipalName={username})))",
    "nested_groups": True, "timeout_seconds": 10,
}
DIRECTORY_GROUPS = [
    {"id": "g-1", "name": "BackROLL-Admins", "group_dn": "CN=BackROLL-Admins,OU=Groups,DC=corp,DC=local", "role": "admin"},
    {"id": "g-2", "name": "BackROLL-Operators", "group_dn": "CN=BackROLL-Operators,OU=Groups,DC=corp,DC=local", "role": "editor"},
    {"id": "g-3", "name": "BackROLL-Readers", "group_dn": "CN=BackROLL-Readers,OU=Groups,DC=corp,DC=local", "role": "viewer"},
]


def directory_view() -> dict:
    return {"config": DIRECTORY, "groups": DIRECTORY_GROUPS}


@app.get(f"{API}/auth/providers")
def providers():
    return {"directory": DIRECTORY["enabled"]}


@app.get(f"{API}/directory")
def get_directory():
    return directory_view()


@app.put(f"{API}/directory")
async def put_directory(request: Request):
    body = await request.json()
    DIRECTORY.update({key: value for key, value in body.items() if key in DIRECTORY and key != "has_bind_password"})
    if body.get("bind_password"):
        DIRECTORY["has_bind_password"] = True
    return directory_view()


@app.post(f"{API}/directory/test")
async def test_directory(request: Request):
    body = await request.json()
    if "unreachable" in (body.get("server_url") or ""):
        return {"ok": False, "message": "The directory could not be reached (ConnectionError)."}
    return {"ok": True, "message": "The directory answers and the search base exists."}


@app.post(f"{API}/directory/lookup")
async def lookup_directory(request: Request):
    body = await request.json()
    people = {
        "alice": {"display_name": "Alice Martin", "groups": ["BackROLL-Admins"], "role": "admin"},
        "bob": {"display_name": "Bob Durand", "groups": ["BackROLL-Operators", "BackROLL-Readers"], "role": "editor"},
        "frank": {"display_name": "Frank Moreau", "groups": [], "role": None},
    }
    person = people.get(body["username"].lower())
    if person is None:
        return {"found": False}
    return {"found": True, "username": body["username"].lower(), "disabled": False, "email": None,
            "dn": f"CN={person['display_name']},OU=Users,DC=corp,DC=local", **person}


@app.post(f"{API}/directory/groups", status_code=201)
async def add_directory_group(request: Request):
    body = await request.json()
    group = {"id": f"g-{len(DIRECTORY_GROUPS) + 1}-{uuid.uuid4().hex[:4]}", "name": body["group"],
             "group_dn": f"CN={body['group']},OU=Groups,DC=corp,DC=local", "role": body["role"]}
    DIRECTORY_GROUPS.append(group)
    return group


@app.patch(f"{API}/directory/groups/{{group_id}}")
async def change_directory_group(group_id: str, request: Request):
    body = await request.json()
    for group in DIRECTORY_GROUPS:
        if group["id"] == group_id:
            group["role"] = body["role"]
    return directory_view()


@app.delete(f"{API}/directory/groups/{{group_id}}")
def remove_directory_group(group_id: str):
    DIRECTORY_GROUPS[:] = [group for group in DIRECTORY_GROUPS if group["id"] != group_id]
    return directory_view()


@app.get(f"{API}/settings")
def settings():
    return {
        "backup_concurrency": 2, "task_history_retention_days": 30, "audit_retention_days": 90,
        "file_browser_ttl_minutes": 30, "storage_alert_percent": 85, "jwt_lifetime_minutes": 480, "login_max_attempts": 5,
        "login_lock_minutes": 15, "backups_running": 1,
        "limits": {
            "backup_concurrency": {"min": 1, "max": 8},
            "task_history_retention_days": {"min": 1, "max": 3650},
            "audit_retention_days": {"min": 1, "max": 3650},
            "file_browser_ttl_minutes": {"min": 5, "max": 1440},
            "storage_alert_percent": {"min": 50, "max": 99},
            "jwt_lifetime_minutes": {"min": 5, "max": 10080},
            "login_max_attempts": {"min": 1, "max": 100},
            "login_lock_minutes": {"min": 1, "max": 1440},
        },
    }


@app.get(f"{API}/dashboard/protection")
def protection(max_age_hours: int = 48):
    result = []
    for repo in repositories():
        recent = repo["age_days"] is not None and repo["age_days"] * 24 <= max_age_hours
        result.append({"name": repo["name"], "state": repo["state"], "last_backup": repo["last_backup"],
                       "protected": recent})
    return {"repositories": result}


@app.get(f"{API}/pools")
def pools():
    return asynchronous(POOLS)


@app.get(f"{API}/hosts")
def hosts():
    return asynchronous(HOSTS)


@app.get(f"{API}/backup_policies")
def policies():
    return asynchronous(POLICIES)


POLICY_PATCHES = []


@app.patch(f"{API}/backup_policies/{{policy_id}}")
def policy_patch(policy_id: str, body: dict):
    POLICY_PATCHES.append({"id": policy_id, **body})
    return {"state": "SUCCESS"}


@app.get("/__mock/policy-patches")
def policy_patches():
    return POLICY_PATCHES


@app.get(f"{API}/storage")
def storage():
    return asynchronous(STORAGE)


@app.get(f"{API}/connectors")
def connectors():
    return asynchronous(CONNECTORS)


@app.get(f"{API}/externalhooks")
def externalhooks():
    return asynchronous(HOOKS)


HOOK_TESTS = []


@app.get(f"{API}/externalhooks/{{hook_id}}/test")
def externalhook_test(hook_id: str):
    HOOK_TESTS.append(hook_id)
    return {"state": "SUCCESS"}


@app.get("/__mock/hook-tests")
def externalhook_tests():
    return {"count": len(HOOK_TESTS)}


@app.get(f"{API}/jobs")
def jobs():
    return asynchronous(JOBS)


@app.get(f"{API}/virtualmachines")
def virtualmachines():
    return asynchronous(VMS)


VM_WARNINGS = []


@app.post("/__mock/vm-warnings")
def set_vm_warnings():
    VM_WARNINGS[:] = ["The connector CS could not be listed (timed out). The machines that only CloudStack knows are missing from this list."]
    return {}


@app.delete("/__mock/vm-warnings")
def clear_vm_warnings():
    VM_WARNINGS.clear()
    return {}


# Before the route of one machine, that would take "warnings" for its identifier.
@app.get(f"{API}/virtualmachines/warnings")
def virtualmachines_warnings():
    return {"warnings": VM_WARNINGS}


@app.get(f"{API}/virtualmachinespaths")
def virtualmachinespaths():
    return {"paths": [{"name": vm["name"], "path": f"/mnt/backup_storage/{vm['name']}"} for vm in VMS]}


@app.get(f"{API}/publickeys")
def publickeys():
    return {"info": [{"name": "id_ed25519.pub",
                      "full_line": "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDemoKeyNotReal backroll@demo"}]}


@app.get(f"{API}/virtualmachines/{{vm_id}}")
def virtualmachine(vm_id: str):
    vm = VM_BY_UUID.get(vm_id)
    name = vm["name"] if vm else "vm"
    return asynchronous({"storage": [{
        "device": "vda", "source": f"/var/lib/libvirt/images/{name}.qcow2",
        "status": {"exists": True, "readable": True}}]})


@app.get(f"{API}/virtualmachines/{{vm_id}}/backups")
def vm_backups(vm_id: str):
    vm = VM_BY_UUID.get(vm_id)
    return asynchronous({"archives": backup_archives(vm) if vm else []})


@app.post(f"{API}/virtualmachines/{{vm_id}}/backups/{{backup}}/files")
def open_files(vm_id: str, backup: str):
    session_id = str(uuid.uuid4())
    result = asynchronous({})
    return {"session_id": session_id, "Location": result["Location"]}


@app.get(f"{API}/file-browser/{{session}}")
def file_session(session: str):
    return {"state": "ready", "filesystems": [], "error": None}


@app.get(f"{API}/file-browser/{{session}}/files")
def file_list(session: str, path: str = "/"):
    path = "/" + path.strip("/") if path.strip("/") else "/"
    return {"path": path, "entries": FILESYSTEM.get(path, [])}


@app.delete(f"{API}/file-browser/{{session}}")
def file_close(session: str):
    return {"state": "SUCCESS"}


@app.get(f"{API}/tasks/backup")
def backup_tasks():
    return {"info": tasks_backup()}


@app.get(f"{API}/tasks/restore")
def restore_tasks():
    return {"info": []}


@app.get(f"{API}/tasks")
def celery_tasks():
    return {"info": tasks_backup()}


@app.get(f"{API}/logs/{{task_id}}")
def logs(task_id: str):
    return json.dumps({"traceback": "Traceback (most recent call last):\n  File \"backup.py\", line 88, in run\n"
                                    "    raise BackupError('Unable to reach the virtual machine')\n"
                                    "BackupError: Unable to reach the virtual machine"})


# Disaster recovery ---------------------------------------------------------------------------

@app.get(f"{API}/drp/repositories")
def drp_repositories(storage_id: str = ""):
    return {"repositories": [vm["name"] for vm in VMS if LAST_BACKUP_DAYS.get(vm["name"]) is not None]}


@app.get(f"{API}/drp/repositories/{{repository}}/archives")
def drp_archives(repository: str, storage_id: str = ""):
    vm = next((v for v in VMS if v["name"] == repository), None)
    archives = [{"disk": "vda", "name": a["name"], "start": a["start"]}
                for a in (backup_archives(vm) if vm else []) if a["name"].startswith("vda_")]
    archives.sort(key=lambda a: a["start"], reverse=True)
    return {"archives": archives}


@app.get(f"{API}/drp/cloudstack/{{connector_id}}/options")
def drp_options(connector_id: str, domain_id: str = "", account: str = ""):
    return CLOUDSTACK_OPTIONS


@app.get(f"{API}/drp/cloudstack/{{connector_id}}/accounts")
def drp_accounts(connector_id: str, domain_id: str = ""):
    return {"accounts": [{"name": "demo"}]}


@app.get(f"{API}/drp/history")
def drp_history(limit: int = 10, offset: int = 0):
    return {"items": DRP_HISTORY[offset:offset + limit], "total": len(DRP_HISTORY)}


@app.get(f"{API}/drp/history/{{run_id}}")
def drp_run(run_id: int):
    for run in DRP_HISTORY:
        if run["id"] == run_id:
            return run
    raise HTTPException(status_code=404, detail="Unknown restore")


# Clean backup
CLEANUP_RUNS = [{
    "id": rid("cleanup", 1), "storage_id": rid("storage", 1), "storage_name": "backup_storage",
    "kind": "prune", "trigger": "manual", "user": "admin",
    "started_at": iso(datetime.now(timezone.utc) - timedelta(hours=3)),
    "finished_at": iso(datetime.now(timezone.utc) - timedelta(hours=3) + timedelta(minutes=4)),
    "status": "success",
    "summary": {"repositories": 6, "archives_deleted": 14, "freed_bytes": 3 * 1024 ** 3, "errors": 0},
    "log": "2026-10-18 02:00:01 6 repository(ies) in /mnt/backup_storage. One backup per day is kept for 30 days.\n"
           "2026-10-18 02:00:05 web-01: Pruning archive (1/2): vda_x_1790000000 Sat, 2026-09-12 02:00:11\n"
           "2026-10-18 02:04:02 14 backup(s) deleted in 6 repository(ies), 3221225472 bytes freed, 0 error(s).",
}]


@app.get(f"{API}/cleanup/settings")
def cleanup_settings():
    return {"storages": [{
        "storage_id": rid("storage", 1), "storage_name": "backup_storage", "path": "/mnt/backup_storage",
        "keep_days": 30, "after_backup": False, "scheduled": True, "schedule": "0 4 * * 0", "hook_id": None}]}


@app.get(f"{API}/cleanup/runs")
def cleanup_runs(limit: int = 50, storage_id: str = ""):
    return {"items": [{k: v for k, v in run.items() if k != "log"} for run in CLEANUP_RUNS]}


@app.get(f"{API}/cleanup/runs/{{run_id}}")
def cleanup_run(run_id: str):
    return next((run for run in CLEANUP_RUNS if run["id"] == run_id), CLEANUP_RUNS[0])


@app.post(f"{API}/cleanup/orphans/scan")
def cleanup_scan():
    result = {"storage_id": rid("storage", 1), "complete": True, "warnings": [], "machines": 6, "orphans": [
        {"name": "i-2-100-VM", "last_backup": iso(datetime.now(timezone.utc) - timedelta(days=45)),
         "archives": 31, "size_bytes": 12 * 1024 ** 3},
        {"name": "old-test-vm", "last_backup": None, "archives": 0, "size_bytes": 4096}]}
    return asynchronous(result)


SELECTION_CALLS = []


@app.post(f"{API}/cleanup/simulate")
def cleanup_simulate():
    def day(days_ago, hour=2):
        return iso(datetime.now(timezone.utc) - timedelta(days=days_ago, hours=hour))
    result = {"storage_id": rid("storage", 1), "keep_days": 30, "archives": 5, "errors": [], "repositories": [
        {"name": "web-01", "total": 7, "kept": 4, "delete": [
            {"name": "vda_x_1", "group": "vda_x", "time": day(80)},
            {"name": "vda_x_2", "group": "vda_x", "time": day(60)},
            {"name": "files_etc_3", "group": "files_etc", "time": day(45)}]},
        {"name": "db-01", "total": 5, "kept": 3, "delete": [
            {"name": "vda_y_1", "group": "vda_y", "time": day(70)},
            {"name": "vda_y_2", "group": "vda_y", "time": day(40)}]}]}
    return asynchronous(result)


@app.post(f"{API}/cleanup/selection/delete")
def cleanup_selection_delete(body: dict):
    SELECTION_CALLS.append(body)
    return {"run_id": rid("cleanup", 1)}


@app.get("/__mock/selection-calls")
def cleanup_selection_calls():
    return SELECTION_CALLS


# Machines whose backups are stopped until an administrator clears them. Empty by default; the tests of the
# interface add one through /__mock/attention.
ATTENTION = []


@app.get(f"{API}/attention")
def attention_list():
    return ATTENTION


@app.post(f"{API}/attention/{{vm_uuid}}/resolve")
def attention_resolve(vm_uuid: str, disk: str | None = None):
    kept = [row for row in ATTENTION if not (row["vm_uuid"] == vm_uuid and (disk is None or row["disk"] == disk))]
    cleared = len(ATTENTION) - len(kept)
    ATTENTION[:] = kept
    if not cleared:
        raise HTTPException(status_code=404)
    return {"cleared": cleared}


@app.post("/__mock/machines")
def machines_add(stopped: int = 0, running: int = 0):
    """Adds machines to see long lists on the dashboard: stopped ones, and running ones that were never backed up."""
    for kind, count, state in (("stopped", stopped, "Shutoff"), ("running", running, "Running")):
        for number in range(1, count + 1):
            name = f"{kind}-{number:03d}"
            vm = {"id": 1000 + len(VMS), "uuid": vm_uuid(name), "name": name, "cpus": 1, "mem": 1024 * 1024,
                  "host": HOSTS[0]["id"], "host_tag": "kvm", "state": state, "pool_id": HOSTS[0]["pool_id"]}
            VMS.append(vm)
            VM_BY_UUID[vm["uuid"]] = vm
    return {"machines": len(VMS)}


@app.delete("/__mock/machines")
def machines_reset():
    """Back to the machines of the demo."""
    VMS[:] = VMS[:len(VM_SPECS)]
    for uuid in [uuid for uuid in VM_BY_UUID if uuid not in {vm["uuid"] for vm in VMS}]:
        del VM_BY_UUID[uuid]
    return {"machines": len(VMS)}


@app.post("/__mock/attention")
def attention_add():
    ATTENTION[:] = [{"vm_uuid": "0498dae1", "vm_name": "i-535-18737-VM", "disk": "vdb", "step": "NEEDS_ATTENTION",
                     "message": "vdb: the machine already writes in an overlay (/mnt/pool/vol-1.snap)",
                     "updated_at": iso(datetime.now(timezone.utc)), "since": iso(datetime.now(timezone.utc))}]
    return {"added": 1}


@app.api_route(f"{API}/{{rest:path}}", methods=["POST", "PUT", "PATCH", "DELETE"])
def write_fallback(rest: str):
    """The screenshots never save anything: every writing route simply succeeds."""
    return {"state": "SUCCESS", **asynchronous({})}


# The built UI ----------------------------------------------------------------------------------

@app.get("/{path:path}")
def spa(path: str):
    if path.startswith("api/"):
        raise HTTPException(status_code=404)
    candidate = (DIST / path).resolve()
    if path and candidate.is_file() and DIST.resolve() in candidate.parents:
        if candidate.suffix == ".js":
            # What the entrypoint of the image does with envsubst.
            text = candidate.read_text(encoding="utf-8").replace("$BACKROLL_VERSION", VERSION)
            return Response(text, media_type="text/javascript")
        return FileResponse(candidate)
    return FileResponse(DIST / "index.html")


def main():
    global DIST
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dist", help="folder of the built UI")
    parser.add_argument("--port", type=int, default=8099)
    args = parser.parse_args()
    DIST = Path(args.dist)
    if not (DIST / "index.html").is_file():
        raise SystemExit(f"{DIST} does not contain a built UI (index.html missing)")
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
