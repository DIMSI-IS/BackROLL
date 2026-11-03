"""Authentication against an Active Directory.

How it works:
 - the user types his directory name and password; BackROLL finds him with a read only account, then asks the
   directory itself to check the password (a bind as the user). The password is never kept;
 - what he may do comes from his groups: each group of the directory is given a role (viewer, editor, admin) in
   Settings. The highest role of his groups applies, nested groups included. A user in no group of the list is
   refused;
 - a user of the directory is also a row of the user table (source "ad"): the audit log, the user page and the
   tokens need one. His role is computed again at each login;
 - local users keep working, whatever happens to the directory.

The access to the directory (`Ldap3Client`) is small and replaceable: everything else is tested with a fake one.
"""

import secrets
import ssl
from dataclasses import dataclass, field
from datetime import datetime, timezone
from urllib.parse import urlparse

from sqlmodel import Session, select

from app import vault
from app.auth.roles import Role
from app.database import DirectoryConfig, DirectoryGroup, User

MASK = "…"
SOURCE = "ad"
MAX_NAME_LENGTH = 64

# The reasons of a refusal, written in the audit log. The user only sees "invalid username or password".
REASONS = {
    "disabled": "the directory is not enabled",
    "unknown_user": "the user is not in the directory",
    "bad_password": "wrong password",
    "account_disabled": "the account is disabled in the directory",
    "no_group": "the user is in none of the groups that give access",
    "deactivated": "the account is deactivated in BackROLL",
    "unavailable": "the directory could not be reached",
    "empty": "no user name or password",
}


class DirectoryError(Exception):
    """The directory could not be asked. The message is safe to show to an administrator."""


@dataclass
class DirectoryUser:
    dn: str
    username: str
    display_name: str | None = None
    email: str | None = None
    disabled: bool = False


@dataclass
class AuthResult:
    ok: bool
    reason: str | None = None
    user: DirectoryUser | None = None
    role: Role | None = None
    groups: list[str] = field(default_factory=list)


# -- the access to the directory ------------------------------------------------------------------------------------

def escape(value: str) -> str:
    from ldap3.utils.conv import escape_filter_chars
    return escape_filter_chars(value)


def clean_username(typed: str) -> str | None:
    """What the user typed, without the domain of "DOMAIN\\user". None when it can not be a name."""
    name = (typed or "").strip()
    if "\\" in name:
        name = name.split("\\", 1)[1]
    if not name or len(name) > 256 or any(ord(c) < 32 for c in name):
        return None
    return name


class Ldap3Client:
    """The directory seen through ldap3. One connection of the service account, one more to check a password."""

    # Replaced in the tests of this class.
    connection_strategy = None

    def __init__(self, config: DirectoryConfig):
        self.config = config
        self.__service = None

    # -- connection

    def _server(self):
        from ldap3 import NONE, Server, Tls
        url = urlparse(self.config.server_url)
        if url.scheme not in ("ldap", "ldaps") or not url.hostname:
            raise DirectoryError("The address of the directory must look like ldaps://dc01.example.com:636.")
        secure = url.scheme == "ldaps"
        tls = Tls(validate=ssl.CERT_REQUIRED if self.config.verify_certificate else ssl.CERT_NONE,
                  ca_certs_data=self.config.ca_certificate or None) if (secure or self.config.start_tls) else None
        return Server(url.hostname, port=url.port or (636 if secure else 389), use_ssl=secure, tls=tls,
                      get_info=NONE, connect_timeout=self.config.timeout_seconds)

    def __connect(self, user: str, password: str):
        from ldap3 import Connection, SYNC
        from ldap3.core.exceptions import LDAPException
        try:
            connection = Connection(
                self._server(), user=user or None, password=password or None, auto_bind=False,
                client_strategy=self.connection_strategy or SYNC, receive_timeout=self.config.timeout_seconds,
                raise_exceptions=False)
            if self.config.start_tls and urlparse(self.config.server_url).scheme == "ldap":
                connection.open()
                connection.start_tls()
            if not connection.bind():
                return connection, False
            return connection, True
        except LDAPException as error:
            raise DirectoryError(f"The directory could not be reached ({type(error).__name__}).") from error
        except OSError as error:
            raise DirectoryError(f"The directory could not be reached ({error.__class__.__name__}).") from error

    def __service_connection(self):
        if self.__service is None:
            try:
                bind_password = vault.decrypt(self.config.bind_password)
            except vault.SecretError as error:
                raise DirectoryError(str(error)) from error
            connection, bound = self.__connect(self.config.bind_dn, bind_password)
            if not bound:
                raise DirectoryError("The directory refused the account that looks for the users: check its name "
                                     "and its password.")
            self.__service = connection
        return self.__service

    def close(self):
        if self.__service is not None:
            try:
                self.__service.unbind()
            except Exception:
                pass
            self.__service = None

    # -- what BackROLL asks

    def test(self) -> dict:
        connection = self.__service_connection()
        from ldap3 import BASE
        found = connection.search(self.config.base_dn, "(objectClass=*)", search_scope=BASE, attributes=["distinguishedName"])
        if not found:
            raise DirectoryError("The search base was not found in the directory: check the base DN.")
        return {"base_dn": self.config.base_dn}

    def find_user(self, username: str) -> DirectoryUser | None:
        from ldap3 import SUBTREE
        connection = self.__service_connection()
        name = clean_username(username)
        if name is None:
            return None
        search_filter = self.config.user_filter.replace("{username}", escape(name))
        connection.search(self.config.base_dn, search_filter, search_scope=SUBTREE, size_limit=2,
                          attributes=["sAMAccountName", "displayName", "mail", "userAccountControl"])
        entries = connection.entries
        if len(entries) != 1:
            # Nobody, or several people for the same name: nobody is chosen for the user.
            return None
        entry = entries[0]

        def value(attribute):
            raw = entry[attribute].value if attribute in entry else None
            return str(raw) if raw not in (None, [], "") else None

        control = value("userAccountControl")
        return DirectoryUser(
            dn=entry.entry_dn, username=value("sAMAccountName") or name, display_name=value("displayName"),
            email=value("mail"), disabled=bool(int(control) & 2) if control and control.isdigit() else False)

    def verify_password(self, user_dn: str, password: str) -> bool:
        # An empty password is an "unauthenticated bind" that many directories accept: never ask.
        if not password:
            return False
        connection, bound = self.__connect(user_dn, password)
        if bound:
            connection.unbind()
        return bound

    def is_member(self, user: DirectoryUser, group_dn: str, nested: bool) -> bool:
        from ldap3 import BASE
        connection = self.__service_connection()
        # 1.2.840.113556.1.4.1941: the groups of the groups, as the directory computes them.
        attribute = "member:1.2.840.113556.1.4.1941:" if nested else "member"
        connection.search(group_dn, f"({attribute}={escape(user.dn)})", search_scope=BASE, attributes=["distinguishedName"])
        return bool(connection.entries)

    def find_group(self, text: str) -> dict | None:
        from ldap3 import BASE, SUBTREE
        connection = self.__service_connection()
        text = text.strip()
        if "=" in text and "," in text:
            found = connection.search(text, "(objectClass=group)", search_scope=BASE, attributes=["cn"])
        else:
            found = connection.search(
                self.config.base_dn, f"(&(objectClass=group)(|(cn={escape(text)})(sAMAccountName={escape(text)})))",
                search_scope=SUBTREE, size_limit=2, attributes=["cn"])
        if not found or len(connection.entries) != 1:
            return None
        entry = connection.entries[0]
        return {"dn": entry.entry_dn, "name": str(entry["cn"].value) if "cn" in entry else entry.entry_dn}


# -- the configuration ------------------------------------------------------------------------------------------------

def get_engine():
    from app.auth.password import get_engine as engine
    return engine()


def get_config(session: Session | None = None) -> DirectoryConfig:
    def read(current: Session) -> DirectoryConfig:
        config = current.get(DirectoryConfig, 1)
        if config is None:
            config = DirectoryConfig(id=1)
            current.add(config)
            current.commit()
            current.refresh(config)
        return config
    if session is not None:
        return read(session)
    with Session(get_engine()) as current:
        config = read(current)
        current.expunge(config)
        return config


def is_enabled() -> bool:
    try:
        return bool(get_config().enabled)
    except Exception:
        return False


def public_config(config: DirectoryConfig) -> dict:
    """What the browser gets: the password of the service account is never sent back."""
    return {
        "enabled": bool(config.enabled), "server_url": config.server_url, "start_tls": bool(config.start_tls),
        "verify_certificate": bool(config.verify_certificate), "ca_certificate": config.ca_certificate or "",
        "base_dn": config.base_dn, "bind_dn": config.bind_dn, "has_bind_password": bool(config.bind_password),
        "user_filter": config.user_filter, "nested_groups": bool(config.nested_groups),
        "timeout_seconds": config.timeout_seconds,
    }


FIELDS = ("enabled", "server_url", "start_tls", "verify_certificate", "ca_certificate", "base_dn", "bind_dn",
          "bind_password", "user_filter", "nested_groups", "timeout_seconds")


def check_address(server_url: str):
    url = urlparse(server_url or "")
    if url.scheme not in ("ldap", "ldaps") or not url.hostname:
        raise ValueError("The address of the directory must look like ldaps://dc01.example.com:636.")


def check_config(values: dict, groups: int):
    url = urlparse(values["server_url"] or "")
    if values["enabled"]:
        check_address(values["server_url"])
        if not values["base_dn"].strip():
            raise ValueError("The search base (base DN) is needed.")
        if groups == 0:
            raise ValueError("Give a role to at least one group first: nobody could log in otherwise.")
    if "{username}" not in values["user_filter"]:
        raise ValueError("The filter that finds the users must contain {username}.")
    if values["start_tls"] and url.scheme == "ldaps":
        raise ValueError("StartTLS is for ldap:// addresses: ldaps:// is already encrypted.")
    if not 2 <= int(values["timeout_seconds"]) <= 60:
        raise ValueError("The time limit must be between 2 and 60 seconds.")
    if values["enabled"] and url.scheme == "ldap" and not values["start_tls"]:
        raise ValueError("Passwords would cross the network in clear: use ldaps://, or ldap:// with StartTLS.")


def merged(config: DirectoryConfig, changes: dict) -> dict:
    """The values of the configuration with the changes of a request. The password is kept when it is not given."""
    values = {name: getattr(config, name) for name in FIELDS}
    for name in FIELDS:
        if name in changes and changes[name] is not None:
            values[name] = changes[name]
    password = changes.get("bind_password")
    if not password or MASK in password:
        values["bind_password"] = config.bind_password
    return values


def save_config(changes: dict) -> dict:
    with Session(get_engine()) as session:
        config = get_config(session)
        values = merged(config, changes)
        groups = len(session.exec(select(DirectoryGroup)).all())
        check_config(values, groups)
        for name, value in values.items():
            # What is typed is encrypted here; what is kept was encrypted when it was typed (or is read as it is).
            setattr(config, name, vault.encrypt(value) if name == "bind_password" else value)
        session.add(config)
        session.commit()
        session.refresh(config)
        return public_config(config)


# -- the groups and their roles ---------------------------------------------------------------------------------------

def list_groups() -> list[dict]:
    with Session(get_engine()) as session:
        rows = session.exec(select(DirectoryGroup).order_by(DirectoryGroup.name)).all()
        return [{"id": str(row.id), "name": row.name, "group_dn": row.group_dn, "role": row.role} for row in rows]


def add_group(group_dn: str, name: str, role: Role) -> dict:
    with Session(get_engine()) as session:
        existing = session.exec(select(DirectoryGroup).where(DirectoryGroup.group_dn == group_dn)).first()
        if existing is not None:
            raise ValueError("This group already has a role.")
        row = DirectoryGroup(group_dn=group_dn, name=name, role=role.value)
        session.add(row)
        session.commit()
        session.refresh(row)
        return {"id": str(row.id), "name": row.name, "group_dn": row.group_dn, "role": row.role}


def change_group_role(group_id, role: Role) -> bool:
    with Session(get_engine()) as session:
        row = session.get(DirectoryGroup, group_id)
        if row is None:
            return False
        row.role = role.value
        session.add(row)
        session.commit()
        return True


def delete_group(group_id) -> bool:
    with Session(get_engine()) as session:
        row = session.get(DirectoryGroup, group_id)
        if row is None:
            return False
        remaining = len(session.exec(select(DirectoryGroup)).all()) - 1
        config = get_config(session)
        if remaining == 0 and config.enabled:
            raise ValueError("The directory is enabled: it needs at least one group. Disable it first.")
        session.delete(row)
        session.commit()
        return True


def role_of_groups(client, user: DirectoryUser, groups: list[dict], nested: bool) -> tuple[Role | None, list[str]]:
    """The highest role among the groups of the list that the user belongs to, and their names."""
    best, matched = None, []
    for group in groups:
        if client.is_member(user, group["group_dn"], nested):
            matched.append(group["name"])
            role = Role(group["role"])
            if best is None or role.rank > best.rank:
                best = role
    return best, matched


# -- the login -----------------------------------------------------------------------------------------------------------

def authenticate(username: str, password: str, client) -> AuthResult:
    """Checks a user with the directory. Raises DirectoryError when the directory can not be asked."""
    name = clean_username(username)
    if name is None or not password:
        return AuthResult(False, "empty")
    user = client.find_user(name)
    if user is None:
        return AuthResult(False, "unknown_user")
    # Looked at first: a directory refuses the bind of a disabled account, which would be written as a wrong password.
    if user.disabled:
        return AuthResult(False, "account_disabled", user)
    if not client.verify_password(user.dn, password):
        return AuthResult(False, "bad_password", user)
    config = get_config()
    role, matched = role_of_groups(client, user, list_groups(), bool(config.nested_groups))
    if role is None:
        return AuthResult(False, "no_group", user)
    return AuthResult(True, None, user, role, matched)


def sync_user(result: AuthResult) -> tuple[User, str | None]:
    """The row of the user table of a user of the directory, created or brought up to date.

    Returns the user and the previous role when the role changed."""
    username = result.user.username.lower()[:MAX_NAME_LENGTH]
    with Session(get_engine()) as session:
        from app.auth.password import find_user_by_name, hash_password
        user = find_user_by_name(session, username)
        previous = None
        if user is None:
            # A password nobody knows: the directory is the only way in.
            user = User(name=username, password_hash=hash_password(secrets.token_urlsafe(24)), auth_source=SOURCE,
                        role=result.role.value)
        elif user.auth_source != SOURCE:
            raise DirectoryError("A local user already has this name.")
        elif user.role != result.role.value:
            previous = user.role
        user.role = result.role.value
        user.external_dn = result.user.dn
        user.display_name = result.user.display_name
        user.email = result.user.email
        user.last_login_at = datetime.now(timezone.utc)
        session.add(user)
        session.commit()
        session.refresh(user)
        return user, previous


# The failed attempts of a name, counted apart from the directory: it would lock the real person otherwise, and
# BackROLL must not become a tool to guess passwords of the directory.
def attempts():
    from app.redis import new_redis_client
    return new_redis_client()


def attempts_key(username: str) -> str:
    return f"directory-login-failures:{(clean_username(username) or '').lower()}"


def is_locked(username: str) -> int:
    """The seconds left before the name may try again, 0 when it may."""
    from app.auth import password
    store = attempts()
    try:
        count = int(store.get(attempts_key(username)) or 0)
        if count >= password.get_max_failed_attempts() > 0:
            return max(int(store.ttl(attempts_key(username))), 1)
        return 0
    finally:
        store.close() if hasattr(store, "close") else None


def count_failure(username: str):
    from app.auth import password
    store = attempts()
    try:
        key = attempts_key(username)
        store.incr(key)
        store.expire(key, int(password.get_lock_duration().total_seconds()) or 900)
    finally:
        store.close() if hasattr(store, "close") else None


def clear_failures(username: str):
    store = attempts()
    try:
        store.delete(attempts_key(username))
    finally:
        store.close() if hasattr(store, "close") else None


def login(username: str, password: str, audit_info: dict | None = None, client_factory=None) -> dict | None:
    """The login payload of a user of the directory, or None. Raises AccountLocked and DirectoryError."""
    from app.auth import password as local

    info = audit_info if audit_info is not None else {}
    info["source"] = SOURCE
    config = get_config()
    if not config.enabled:
        info["detail"] = f"refused: {REASONS['disabled']}"
        return None

    remaining = is_locked(username)
    if remaining:
        info["detail"] = "refused: too many failed attempts"
        raise local.AccountLocked(remaining)

    client = (client_factory or Ldap3Client)(config)
    try:
        try:
            result = authenticate(username, password, client)
        except DirectoryError as error:
            info["detail"] = f"refused: {REASONS['unavailable']} ({error})"
            raise
    finally:
        client.close()

    if not result.ok:
        info["detail"] = f"refused: {REASONS[result.reason]}"
        if result.reason in ("unknown_user", "bad_password"):
            count_failure(username)
        return None

    user, previous = sync_user(result)
    if not user.is_active:
        info["detail"] = f"refused: {REASONS['deactivated']}"
        return None
    clear_failures(username)
    groups = ", ".join(result.groups)
    info["detail"] = (f"role={result.role.value} from {groups}"
                      + (f" (was {previous})" if previous else ""))
    return local.login_payload(user)
