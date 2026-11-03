from datetime import datetime, timedelta, timezone
from logging import Logger

from fastapi import Request
from sqlmodel import Session, col, delete

from app import settings
from app.auth.password import get_engine
from app.database import AuditLog
from app.logging import logged

MAX_DETAIL_LENGTH = 1024

# Requests that do not change anything, although they use a writing method.
IGNORED = set()

# Requests that change something, although they use the GET method.
LOGGED_GET = {
    "/api/v1/virtualmachines/{virtual_machine_id}/breaklock",
    "/api/v1/externalhooks/{hook_id}/test",
    "/api/v1/file-browser/{session_id}/download",
}

# Routes whose caller is not authenticated by a token: the user name comes from the route.
AUTH_ROUTES = {
    "/api/v1/auth/password/login",
    "/api/v1/auth/cloudstack/login",
    "/api/v1/auth/setup",
}

RESOURCES = {
    "pools": "Pool",
    "hosts": "Hypervisor",
    "storage": "Storage",
    "connectors": "Connector",
    "externalhooks": "External hook",
    "backup_policies": "Backup policy",
    "users": "User",
}

VERBS = {"POST": "created", "PATCH": "updated", "PUT": "updated", "DELETE": "deleted"}

ACTIONS = {
    ("POST", "/api/v1/auth/password/login"): "Login",
    ("POST", "/api/v1/auth/cloudstack/login"): "Login (CloudStack)",
    ("POST", "/api/v1/auth/password/change"): "Password changed",
    ("POST", "/api/v1/auth/setup"): "Administrator account created",
    ("POST", "/api/v1/tasks/singlebackup/{virtual_machine_id}"): "Backup started (virtual machine)",
    ("POST", "/api/v1/tasks/poolbackup/{pool_id}"): "Backup started (pool)",
    ("POST", "/api/v1/tasks/restore/{virtual_machine_id}"): "Restore started",
    ("DELETE", "/api/v1/virtualmachines/{virtual_machine_id}/backups/{backup_name}"): "Backup deleted",
    ("GET", "/api/v1/virtualmachines/{virtual_machine_id}/breaklock"): "Backup repository unlocked",
    ("GET", "/api/v1/externalhooks/{hook_id}/test"): "External hook tested",
    ("POST", "/api/v1/connect/{host_id}"): "Hypervisor SSH connection initialized",
    ("POST", "/api/v1/virtualmachines/{virtual_machine_id}/backups/{backup_name}/files"): "Backup files opened",
    ("GET", "/api/v1/file-browser/{session_id}/download"): "File downloaded from a backup",
    ("DELETE", "/api/v1/file-browser/{session_id}"): "Backup files closed",
    ("POST", "/api/v1/drp/restore"): "VM restored to a new CloudStack VM",
    ("POST", "/api/v1/file-browser/{session_id}/filesystem"): "Backup filesystem chosen",
    ("PUT", "/api/v1/settings"): "Settings changed",
    ("PUT", "/api/v1/directory"): "Active Directory settings changed",
    ("POST", "/api/v1/directory/test"): "Active Directory connection tested",
    ("POST", "/api/v1/directory/lookup"): "Active Directory user looked up",
    ("POST", "/api/v1/directory/groups"): "Active Directory group given a role",
    ("PATCH", "/api/v1/directory/groups/{group_id}"): "Role of an Active Directory group changed",
    ("DELETE", "/api/v1/directory/groups/{group_id}"): "Active Directory group removed",
    ("POST", "/api/v1/attention/{vm_uuid}/resolve"): "Disks of a machine cleared after a check",
    ("PUT", "/api/v1/cleanup/settings/{storage_id}"): "Cleanup settings changed",
    ("POST", "/api/v1/cleanup/run"): "Cleanup of the old backups started",
    ("POST", "/api/v1/cleanup/orphans/scan"): "Search for the backups of deleted machines",
    ("POST", "/api/v1/cleanup/orphans/delete"): "Backups of deleted machines deleted",
}


def describe(method: str, route_path: str) -> str:
    action = ACTIONS.get((method, route_path))
    if action:
        return action

    # Routes like /api/v1/pools or /api/v1/pools/{pool_id}.
    segments = route_path.removeprefix("/api/v1/").split("/")
    resource = RESOURCES.get(segments[0])
    if resource and method in VERBS:
        return f"{resource} {VERBS[method]}"

    return f"{method} {route_path}"


def should_log(method: str, route_path: str, has_identity: bool) -> bool:
    if (method, route_path) in IGNORED:
        return False
    if method == "POST" and route_path in AUTH_ROUTES:
        return True
    if not has_identity:
        return False
    if method in ("POST", "PUT", "PATCH", "DELETE"):
        return True
    return method == "GET" and route_path in LOGGED_GET


def set_detail(request: Request, detail: str):
    request.state.audit_detail = detail


def set_source(request: Request, source: str):
    """Where the user was authenticated, for the routes that log him in ("local" or "ad")."""
    request.state.audit_source = source


def set_username(request: Request, username: str):
    """For the routes where the caller is not authenticated yet, such as the login."""
    request.state.audit_username = username


def get_client_ip(request: Request) -> str | None:
    # The nginx proxy adds the address of the client at the END of this header: what comes before
    # was written by the client and is not to be trusted.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[-1].strip()
    return request.client.host if request.client else None


@logged(bounds=False)
def record(request: Request, status_code: int, logger: Logger):
    """Never raises: an audit failure must not break the request."""
    try:
        route = request.scope.get("route")
        if route is None:
            return
        route_path = route.path

        identity = getattr(request.state, "identity", None)
        if not should_log(request.method, route_path, identity is not None):
            return

        details = [f"{key}={value}" for key, value in request.path_params.items()]
        custom = getattr(request.state, "audit_detail", None)
        if custom:
            details.append(custom)

        entry = AuditLog(
            user_id=identity["id"] if identity else None,
            username=(identity["username"] if identity
                      else getattr(request.state, "audit_username", None)),
            action=describe(request.method, route_path),
            method=request.method,
            path=request.url.path,
            status_code=status_code,
            ip_address=get_client_ip(request),
            detail=", ".join(details)[:MAX_DETAIL_LENGTH] or None,
            source=(getattr(request.state, "audit_source", None)
                    or (identity.get("auth_source") if identity else None) or "local"),
        )
        with Session(get_engine()) as session:
            session.add(entry)
            session.commit()
    except Exception as exception:
        logger.error(f"Unable to write the audit log. {exception}")


@logged()
def purge_old_entries(logger: Logger):
    days = settings.get_audit_retention_days()
    limit = datetime.now(timezone.utc) - timedelta(days=days)
    with Session(get_engine()) as session:
        session.exec(delete(AuditLog).where(col(AuditLog.created_at) < limit))
        session.commit()
    logger.info(f"Audit entries older than {days} days are purged.")
