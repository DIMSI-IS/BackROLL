"""Authentication against an Active Directory: the groups that give a role, the refusals, the audit log.

A fake directory in memory plays the Active Directory; the real client (ldap3) is tried on a mock directory of ldap3.
"""

import json

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, delete, select

pytest.importorskip("ldap3")

from app import vault  # noqa: E402
from app.auth import directory, password  # noqa: E402
from app.auth.roles import Role  # noqa: E402
from app.database import AuditLog, DirectoryConfig, DirectoryGroup, User, init_db_connection, migrate_audit_table, migrate_user_table  # noqa: E402
from app.initialized import fastapi_app  # noqa: E402
from app.routes import audit as audit_routes  # noqa: E402,F401
from app.routes import users as users_routes  # noqa: E402,F401
from app.routes.auth import directory as directory_routes  # noqa: E402,F401
from app.routes.auth import password as password_routes  # noqa: E402,F401

ADMINS = "CN=BackROLL-Admins,OU=Groups,DC=corp,DC=local"
OPERATORS = "CN=BackROLL-Operators,OU=Groups,DC=corp,DC=local"
READERS = "CN=BackROLL-Readers,OU=Groups,DC=corp,DC=local"


class FakeDirectory:
    """The directory of the tests. `users` maps a name to its password, state and groups."""
    users: dict = {}
    reachable = True
    instances: list = []

    def __init__(self, config):
        self.config = config
        self.closed = False
        FakeDirectory.instances.append(self)

    def __ask(self):
        if not FakeDirectory.reachable:
            raise directory.DirectoryError("The directory could not be reached (ConnectionError).")

    def find_user(self, username):
        self.__ask()
        name = directory.clean_username(username)
        entry = FakeDirectory.users.get((name or "").lower())
        if entry is None:
            return None
        return directory.DirectoryUser(dn=entry["dn"], username=entry["name"], display_name=entry.get("display_name"),
                                       email=entry.get("email"), disabled=entry.get("disabled", False))

    def verify_password(self, dn, password):
        self.__ask()
        return bool(password) and any(e["dn"] == dn and e["password"] == password for e in FakeDirectory.users.values())

    def is_member(self, user, group_dn, nested):
        self.__ask()
        entry = next(e for e in FakeDirectory.users.values() if e["dn"] == user.dn)
        return group_dn in entry["groups"] or (nested and group_dn in entry.get("nested_groups", ()))

    def find_group(self, text):
        self.__ask()
        known = {"BackROLL-Admins": ADMINS, "BackROLL-Operators": OPERATORS, "BackROLL-Readers": READERS}
        dn = known.get(text, text if text in known.values() else None)
        return {"dn": dn, "name": dn.split(",")[0][3:]} if dn else None

    def test(self):
        self.__ask()
        return {"base_dn": self.config.base_dn}

    def close(self):
        self.closed = True


class FakeStore:
    """The counters of failed logins, in memory."""
    data: dict = {}

    def get(self, key):
        return FakeStore.data.get(key)

    def incr(self, key):
        FakeStore.data[key] = int(FakeStore.data.get(key, 0)) + 1

    def expire(self, key, seconds):
        pass

    def ttl(self, key):
        return 600

    def delete(self, key):
        FakeStore.data.pop(key, None)

    def close(self):
        pass


def person(name, groups=(), nested=(), **more):
    return {"name": name, "dn": f"CN={name},OU=Users,DC=corp,DC=local", "password": f"{name}-secret", "groups": set(groups),
            "nested_groups": set(nested), "display_name": name.title(), "email": f"{name}@corp.local", **more}


@pytest.fixture
def world(monkeypatch):
    engine = init_db_connection()
    SQLModel.metadata.create_all(engine)
    migrate_user_table(engine)
    migrate_audit_table(engine)
    with Session(engine) as session:
        session.exec(delete(DirectoryGroup))
        session.exec(delete(DirectoryConfig))
        session.exec(delete(User).where(User.auth_source == "ad"))
        session.add(DirectoryConfig(id=1, enabled=True, server_url="ldaps://dc.corp.local:636", base_dn="DC=corp,DC=local",
                                    bind_dn="CN=svc,OU=Users,DC=corp,DC=local", bind_password="svc-secret"))
        for dn, role in ((ADMINS, "admin"), (OPERATORS, "editor"), (READERS, "viewer")):
            session.add(DirectoryGroup(group_dn=dn, name=dn.split(",")[0][3:], role=role))
        session.commit()
    FakeDirectory.users = {
        "alice": person("alice", [ADMINS]), "bob": person("bob", [OPERATORS]), "carol": person("carol", [READERS]),
        "dave": person("dave", [OPERATORS, READERS]), "erin": person("erin", [], nested=[ADMINS]),
        "frank": person("frank", []), "grace": person("grace", [ADMINS], disabled=True),
    }
    FakeDirectory.reachable, FakeDirectory.instances = True, []
    FakeStore.data = {}
    monkeypatch.setattr(directory, "Ldap3Client", FakeDirectory)
    monkeypatch.setattr(directory, "attempts", lambda: FakeStore())
    return engine


def login(name, secret=None):
    info = {}
    payload = password.login(name, secret if secret is not None else f"{name}-secret", info)
    return payload, info


# -- the role comes from the groups -----------------------------------------------------------------------------------

@pytest.mark.parametrize("name,role", [("alice", "admin"), ("bob", "editor"), ("carol", "viewer")])
def test_the_role_is_the_one_of_the_group(world, name, role):
    payload, info = login(name)
    assert payload["user"]["role"] == role and payload["user"]["auth_source"] == "ad"
    assert info["source"] == "ad" and f"role={role}" in info["detail"]


def test_a_user_of_several_groups_gets_the_highest_role(world):
    payload, info = login("dave")
    assert payload["user"]["role"] == "editor"
    assert "BackROLL-Operators" in info["detail"] and "BackROLL-Readers" in info["detail"]


def test_a_group_of_a_group_gives_its_role_when_the_nested_groups_are_on(world):
    assert login("erin")[0]["user"]["role"] == "admin"
    with Session(world) as session:
        config = session.get(DirectoryConfig, 1)
        config.nested_groups = False
        session.add(config)
        session.commit()
    assert login("erin")[0] is None


def test_the_role_follows_the_groups_at_each_login(world):
    assert login("bob")[0]["user"]["role"] == "editor"
    FakeDirectory.users["bob"]["groups"] = {ADMINS}
    payload, info = login("bob")
    assert payload["user"]["role"] == "admin" and "was editor" in info["detail"]
    # The same row is used: nothing is duplicated.
    with Session(world) as session:
        assert len(session.exec(select(User).where(User.name == "bob")).all()) == 1


def test_the_user_keeps_his_name_his_mail_and_his_last_login(world):
    payload, _ = login("alice")
    assert payload["user"]["display_name"] == "Alice" and payload["user"]["email"] == "alice@corp.local"
    assert payload["user"]["last_login_at"]


# -- the refusals -------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("name,secret,reason", [
    ("alice", "wrong", "wrong password"), ("nobody", "x", "not in the directory"),
    ("frank", "frank-secret", "none of the groups"), ("grace", "grace-secret", "disabled in the directory"),
    ("alice", "", "no user name or password")])
def test_a_refusal_says_why_in_the_audit_detail_and_gives_nothing(world, name, secret, reason):
    payload, info = login(name, secret)
    assert payload is None
    assert reason in info["detail"] and info["source"] == "ad"


def test_a_disabled_account_is_reported_as_disabled_even_with_a_wrong_password(world):
    # A real directory refuses the bind of a disabled account: the reason must not be "wrong password".
    payload, info = login("grace", "wrong")
    assert payload is None and "disabled in the directory" in info["detail"]
    assert FakeStore.data == {}


def test_a_user_in_no_group_is_not_created(world):
    login("frank")
    with Session(world) as session:
        assert session.exec(select(User).where(User.name == "frank")).first() is None


def test_an_empty_password_never_reaches_the_directory(world):
    # An "unauthenticated bind" with an empty password is accepted by many directories.
    assert login("alice", "")[0] is None
    assert FakeDirectory.instances == [] or all(i.closed for i in FakeDirectory.instances)


def test_the_domain_typed_before_the_name_is_ignored(world):
    assert login("CORP\\alice", "alice-secret")[0]["user"]["name"] == "alice"


def test_a_user_deactivated_in_backroll_is_refused_whatever_the_directory_says(world):
    login("bob")
    with Session(world) as session:
        user = session.exec(select(User).where(User.name == "bob")).one()
        user.is_active = False
        session.add(user)
        session.commit()
    payload, info = login("bob")
    assert payload is None and "deactivated in BackROLL" in info["detail"]


def test_a_directory_that_is_off_gives_nobody_a_session(world):
    with Session(world) as session:
        config = session.get(DirectoryConfig, 1)
        config.enabled = False
        session.add(config)
        session.commit()
    # An unknown name is a local login, which fails; a user already known as "ad" is refused too.
    assert password.login("alice", "alice-secret") is None
    login_before = password.login("alice", "alice-secret", {})
    assert login_before is None


def test_a_user_of_the_directory_who_loses_his_groups_is_refused(world):
    assert login("bob")[0]
    FakeDirectory.users["bob"]["groups"] = set()
    assert login("bob")[0] is None


def test_a_directory_that_does_not_answer_is_an_error_not_a_refusal(world):
    FakeDirectory.reachable = False
    info = {}
    with pytest.raises(directory.DirectoryError):
        password.login("alice", "alice-secret", info)
    assert "could not be reached" in info["detail"]
    assert all(instance.closed for instance in FakeDirectory.instances)


# -- the failed attempts --------------------------------------------------------------------------------------------------

def test_a_name_that_fails_too_often_is_locked_without_asking_the_directory(world):
    for _ in range(password.get_max_failed_attempts()):
        assert login("alice", "wrong")[0] is None
    asked = len(FakeDirectory.instances)
    with pytest.raises(password.AccountLocked):
        login("alice")
    assert len(FakeDirectory.instances) == asked
    # Another name is not concerned.
    assert login("bob")[0]


def test_a_good_login_forgets_the_failures(world):
    login("alice", "wrong")
    login("alice", "wrong")
    assert login("alice")[0]
    assert FakeStore.data == {}


def test_a_failure_of_a_user_who_has_no_right_does_not_count(world):
    login("frank")
    assert FakeStore.data == {}


# -- local users and the directory ------------------------------------------------------------------------------------------

def test_a_local_user_is_checked_by_backroll_even_when_the_directory_is_on(world):
    with Session(world) as session:
        session.add(User(name="localadmin", password_hash=password.hash_password("local-password"), role="admin"))
        session.commit()
    assert password.login("localadmin", "local-password")["user"]["auth_source"] == "local"
    FakeDirectory.reachable = False
    assert password.login("localadmin", "local-password")["user"]["name"] == "localadmin"
    assert password.login("localadmin", "wrong") is None


def test_a_local_user_with_the_name_of_a_user_of_the_directory_keeps_the_name(world):
    with Session(world) as session:
        session.add(User(name="alice", password_hash=password.hash_password("alice-local-password"), role="viewer"))
        session.commit()
    # The local account is the one that answers: the directory is not asked, its password does not work.
    assert password.login("alice", "alice-secret") is None
    assert password.login("alice", "alice-local-password")["user"]["auth_source"] == "local"
    with Session(world) as session:
        session.exec(delete(User).where(User.name == "alice"))
        session.commit()


# -- the API ------------------------------------------------------------------------------------------------------------------

@pytest.fixture
def client(world):
    with Session(world) as session:
        if password.find_user_by_name(session, "dir-admin") is None:
            session.add(User(name="dir-admin", password_hash=password.hash_password("dir-admin-password"), role="admin"))
        session.commit()
    return TestClient(fastapi_app)


def local_headers(client):
    token = client.post("/api/v1/auth/password/login", json={"username": "dir-admin", "password": "dir-admin-password"}).json()
    return {"Authorization": f"Bearer {token['access_token']}"}


def test_a_user_of_the_directory_logs_in_through_the_api_and_has_the_rights_of_his_role(client):
    answer = client.post("/api/v1/auth/password/login", json={"username": "bob", "password": "bob-secret"})
    assert answer.status_code == 200 and answer.json()["user"]["role"] == "editor"
    headers = {"Authorization": f"Bearer {answer.json()['access_token']}"}
    assert client.get("/api/v1/auth/me", headers=headers).json()["role"] == "editor"
    # An editor does not manage the users, an administrator of the directory does.
    assert client.get("/api/v1/users", headers=headers).status_code == 403
    admin = client.post("/api/v1/auth/password/login", json={"username": "alice", "password": "alice-secret"}).json()
    assert client.get("/api/v1/users", headers={"Authorization": f"Bearer {admin['access_token']}"}).status_code == 200


def test_a_refused_user_gets_the_same_answer_whatever_the_reason(client):
    answers = {client.post("/api/v1/auth/password/login", json={"username": n, "password": p}).json()["detail"]
               for n, p in (("alice", "wrong"), ("nobody", "x"), ("frank", "frank-secret"), ("grace", "grace-secret"))}
    assert answers == {"Invalid username or password."}


def test_a_directory_that_is_down_is_told_to_the_user(client):
    FakeDirectory.reachable = False
    answer = client.post("/api/v1/auth/password/login", json={"username": "alice", "password": "alice-secret"})
    assert answer.status_code == 503 and "Active Directory" in answer.json()["detail"]


def test_too_many_failures_answer_429(client):
    for _ in range(password.get_max_failed_attempts()):
        client.post("/api/v1/auth/password/login", json={"username": "alice", "password": "wrong"})
    answer = client.post("/api/v1/auth/password/login", json={"username": "alice", "password": "alice-secret"})
    assert answer.status_code == 429


def test_the_audit_log_tells_the_source_the_user_and_the_reason(client, world):
    client.post("/api/v1/auth/password/login", json={"username": "alice", "password": "alice-secret"})
    client.post("/api/v1/auth/password/login", json={"username": "frank", "password": "frank-secret"})
    client.post("/api/v1/auth/password/login", json={"username": "dir-admin", "password": "dir-admin-password"})
    headers = local_headers(client)
    ad = client.get("/api/v1/audit?source=ad&limit=50", headers=headers).json()["items"]
    names = {entry["username"]: entry for entry in ad}
    assert {"alice", "frank"} <= set(names) and "dir-admin" not in names
    assert names["alice"]["source"] == "ad" and "role=admin" in names["alice"]["detail"] and names["alice"]["status_code"] == 200
    assert names["frank"]["status_code"] == 401 and "none of the groups" in names["frank"]["detail"]
    local = client.get("/api/v1/audit?source=local&limit=50", headers=headers).json()["items"]
    assert any(entry["username"] == "dir-admin" for entry in local) and not any(entry["source"] == "ad" for entry in local)


def test_the_actions_of_a_user_of_the_directory_are_logged_with_his_source(client, world):
    token = client.post("/api/v1/auth/password/login", json={"username": "alice", "password": "alice-secret"}).json()
    headers = {"Authorization": f"Bearer {token['access_token']}"}
    assert client.get("/api/v1/directory", headers=headers).status_code == 200
    client.put("/api/v1/directory", headers=headers, json={"timeout_seconds": 12})
    entries = client.get("/api/v1/audit?source=ad&action=Active%20Directory&limit=20", headers=headers).json()["items"]
    assert any(e["username"] == "alice" and e["action"] == "Active Directory settings changed" and e["source"] == "ad"
               for e in entries)


def test_a_user_of_the_directory_has_no_password_to_change_or_to_reset(client, world):
    token = client.post("/api/v1/auth/password/login", json={"username": "bob", "password": "bob-secret"}).json()
    headers = {"Authorization": f"Bearer {token['access_token']}"}
    answer = client.post("/api/v1/auth/password/change", headers=headers,
                         json={"old_password": "x", "new_password": "a-new-password"})
    assert answer.status_code == 400 and "Active Directory" in answer.json()["detail"]
    admin = local_headers(client)
    bob = next(u for u in client.get("/api/v1/users", headers=admin).json() if u["name"] == "bob")
    assert bob["auth_source"] == "ad"
    assert client.patch(f"/api/v1/users/{bob['id']}", headers=admin, json={"role": "admin"}).status_code == 409
    assert client.patch(f"/api/v1/users/{bob['id']}", headers=admin, json={"password": "a-new-password"}).status_code == 409
    # He can be deactivated, which refuses his next login.
    assert client.patch(f"/api/v1/users/{bob['id']}", headers=admin, json={"is_active": False}).status_code == 200


# -- the settings ------------------------------------------------------------------------------------------------------------

def test_the_settings_never_give_the_password_of_the_service_account(client):
    body = client.get("/api/v1/directory", headers=local_headers(client)).json()
    assert body["config"]["has_bind_password"] is True and "bind_password" not in body["config"]
    assert "svc-secret" not in json.dumps(body)


def test_the_settings_keep_the_password_when_it_is_not_given_or_masked(client, world):
    headers = local_headers(client)
    client.put("/api/v1/directory", headers=headers, json={"timeout_seconds": 15, "bind_password": ""})
    client.put("/api/v1/directory", headers=headers, json={"bind_password": f"s{directory.MASK}"})
    with Session(world) as session:
        # The password stored in clear before the encryption existed is kept, and encrypted by this save.
        assert vault.decrypt(session.get(DirectoryConfig, 1).bind_password) == "svc-secret"
        assert vault.is_encrypted(session.get(DirectoryConfig, 1).bind_password)
    client.put("/api/v1/directory", headers=headers, json={"bind_password": "a-new-secret"})
    with Session(world) as session:
        stored = session.get(DirectoryConfig, 1).bind_password
    # What is typed is encrypted in the database, and can be read back with the key.
    assert stored.startswith(vault.PREFIX) and "a-new-secret" not in stored
    assert vault.decrypt(stored) == "a-new-secret"
    # Saved again without the password: the encrypted value is kept as it is.
    client.put("/api/v1/directory", headers=headers, json={"timeout_seconds": 16})
    with Session(world) as session:
        assert session.get(DirectoryConfig, 1).bind_password == stored


# -- the encryption of the secrets ------------------------------------------------------------------------------------------------

def test_a_secret_is_encrypted_and_read_back():
    encrypted = vault.encrypt("svc-secret")
    assert encrypted.startswith("enc1:") and "svc-secret" not in encrypted
    assert vault.decrypt(encrypted) == "svc-secret"
    # Two encryptions of the same secret differ: nothing can be compared in the database.
    assert vault.encrypt("svc-secret") != encrypted
    # Encrypting twice does not encrypt twice.
    assert vault.encrypt(encrypted) == encrypted
    assert vault.encrypt("") == "" and vault.decrypt("") == ""


def test_a_secret_stored_before_the_encryption_is_read_as_it_is():
    assert vault.decrypt("old-plain-password") == "old-plain-password"
    assert not vault.is_encrypted("old-plain-password") and vault.is_encrypted(vault.encrypt("x"))


def test_another_key_can_not_read_the_secret_and_says_what_to_do(monkeypatch):
    monkeypatch.setenv("SECRETS_KEY", "first-key")
    encrypted = vault.encrypt("svc-secret")
    monkeypatch.setenv("SECRETS_KEY", "second-key")
    with pytest.raises(vault.SecretError, match="Type it again"):
        vault.decrypt(encrypted)
    monkeypatch.setenv("SECRETS_KEY", "first-key")
    assert vault.decrypt(encrypted) == "svc-secret"


def test_the_key_is_the_one_of_the_settings_or_the_secret_of_the_tokens(monkeypatch):
    monkeypatch.delenv("SECRETS_KEY", raising=False)
    monkeypatch.setenv("JWT_SECRET", "x" * 40)
    first = vault.encrypt("a")
    monkeypatch.setenv("SECRETS_KEY", "dedicated")
    with pytest.raises(vault.SecretError):
        vault.decrypt(first)
    monkeypatch.delenv("SECRETS_KEY")
    monkeypatch.delenv("JWT_SECRET")
    with pytest.raises(vault.SecretError, match="No key"):
        vault.encrypt("a")


@pytest.mark.parametrize("changes,message", [
    ({"server_url": "dc.corp.local"}, "address of the directory"),
    ({"server_url": "ldap://dc.corp.local"}, "in clear"),
    ({"user_filter": "(sAMAccountName=x)"}, "{username}"),
    ({"server_url": "ldaps://dc.corp.local", "start_tls": True}, "StartTLS"),
    ({"base_dn": " "}, "search base")])
def test_the_settings_refuse_what_would_lock_everybody_out_or_send_passwords_in_clear(client, changes, message):
    answer = client.put("/api/v1/directory", headers=local_headers(client), json=changes)
    assert answer.status_code == 422 and message in answer.json()["detail"]


def test_the_directory_can_not_be_enabled_without_a_group(client, world):
    with Session(world) as session:
        session.exec(delete(DirectoryGroup))
        config = session.get(DirectoryConfig, 1)
        config.enabled = False
        session.add(config)
        session.commit()
    answer = client.put("/api/v1/directory", headers=local_headers(client), json={"enabled": True})
    assert answer.status_code == 422 and "at least one group" in answer.json()["detail"]


def test_the_last_group_can_not_be_removed_while_the_directory_is_on(client, world):
    headers = local_headers(client)
    groups = client.get("/api/v1/directory", headers=headers).json()["groups"]
    for group in groups[:-1]:
        assert client.delete(f"/api/v1/directory/groups/{group['id']}", headers=headers).status_code == 200
    assert client.delete(f"/api/v1/directory/groups/{groups[-1]['id']}", headers=headers).status_code == 409


def test_groups_are_given_a_role_found_in_the_directory_and_can_change_role(client):
    headers = local_headers(client)
    unknown = client.post("/api/v1/directory/groups", headers=headers, json={"group": "Nobody", "role": "viewer"})
    assert unknown.status_code == 404
    with Session(init_db_connection()) as session:
        session.exec(delete(DirectoryGroup).where(DirectoryGroup.group_dn == READERS))
        session.commit()
    created = client.post("/api/v1/directory/groups", headers=headers, json={"group": "BackROLL-Readers", "role": "viewer"})
    assert created.status_code == 201 and created.json()["group_dn"] == READERS
    again = client.post("/api/v1/directory/groups", headers=headers, json={"group": READERS, "role": "editor"})
    assert again.status_code == 409
    changed = client.patch(f"/api/v1/directory/groups/{created.json()['id']}", headers=headers, json={"role": "editor"})
    assert changed.status_code == 200
    assert {g["name"]: g["role"] for g in changed.json()["groups"]}["BackROLL-Readers"] == "editor"


def test_the_lookup_of_a_user_shows_the_role_he_would_get_without_his_password(client):
    headers = local_headers(client)
    found = client.post("/api/v1/directory/lookup", headers=headers, json={"username": "dave"}).json()
    assert found["found"] and found["role"] == "editor" and set(found["groups"]) == {"BackROLL-Operators", "BackROLL-Readers"}
    assert client.post("/api/v1/directory/lookup", headers=headers, json={"username": "nobody"}).json() == {"found": False}
    nothing = client.post("/api/v1/directory/lookup", headers=headers, json={"username": "frank"}).json()
    assert nothing["found"] and nothing["role"] is None


def test_the_connection_test_says_what_is_wrong(client):
    headers = local_headers(client)
    assert client.post("/api/v1/directory/test", headers=headers, json={}).json()["ok"] is True
    FakeDirectory.reachable = False
    answer = client.post("/api/v1/directory/test", headers=headers, json={}).json()
    assert answer["ok"] is False and "could not be reached" in answer["message"]
    bad = client.post("/api/v1/directory/test", headers=headers, json={"server_url": "nonsense"}).json()
    assert bad["ok"] is False and "address" in bad["message"]


# -- the real client, on a directory of ldap3 -----------------------------------------------------------------------------------

@pytest.fixture
def mock_directory():
    from ldap3 import MOCK_SYNC, OFFLINE_AD_2012_R2, Connection, Server

    server = Server("mock-dc", get_info=OFFLINE_AD_2012_R2)
    seed = Connection(server, user="CN=svc,OU=Users,DC=corp,DC=local", password="svc-secret", client_strategy=MOCK_SYNC)
    seed.strategy.add_entry("DC=corp,DC=local", {"objectClass": "domain", "dc": "corp"})
    seed.strategy.add_entry("CN=svc,OU=Users,DC=corp,DC=local", {"userPassword": "svc-secret", "objectClass": "user"})
    seed.strategy.add_entry("CN=alice,OU=Users,DC=corp,DC=local", {
        "userPassword": "alice-secret", "objectClass": ["top", "person", "user"], "objectCategory": "person",
        "sAMAccountName": "alice", "displayName": "Alice A", "mail": "alice@corp.local", "userAccountControl": 512})
    seed.strategy.add_entry("CN=gina,OU=Users,DC=corp,DC=local", {
        "userPassword": "gina-secret", "objectClass": ["top", "person", "user"], "objectCategory": "person",
        "sAMAccountName": "gina", "userAccountControl": 514})
    seed.strategy.add_entry(ADMINS, {"objectClass": "group", "cn": "BackROLL-Admins",
                                     "member": ["CN=alice,OU=Users,DC=corp,DC=local"]})

    class MockClient(directory.Ldap3Client):
        connection_strategy = MOCK_SYNC

        def _server(self):
            return server

    seed.bind()
    return MockClient


def mock_config():
    return DirectoryConfig(id=1, enabled=True, server_url="ldaps://mock-dc:636", base_dn="DC=corp,DC=local",
                           bind_dn="CN=svc,OU=Users,DC=corp,DC=local", bind_password="svc-secret", verify_certificate=False)


def test_the_real_client_finds_a_user_and_checks_his_password(mock_directory):
    client = mock_directory(mock_config())
    user = client.find_user("alice")
    assert user.dn == "CN=alice,OU=Users,DC=corp,DC=local" and user.username == "alice"
    assert user.display_name == "Alice A" and user.email == "alice@corp.local" and user.disabled is False
    assert client.verify_password(user.dn, "alice-secret") is True
    assert client.verify_password(user.dn, "wrong") is False
    assert client.verify_password(user.dn, "") is False
    assert client.find_user("nobody") is None
    assert client.find_user("alice)(|(sAMAccountName=*") is None  # the filter can not be bent by what is typed
    client.close()


def test_the_real_client_sees_a_disabled_account_and_a_group(mock_directory):
    client = mock_directory(mock_config())
    assert client.find_user("gina").disabled is True
    alice = client.find_user("alice")
    assert client.is_member(alice, ADMINS, nested=False) is True
    assert client.is_member(client.find_user("gina"), ADMINS, nested=False) is False
    assert client.find_group(ADMINS) == {"dn": ADMINS, "name": "BackROLL-Admins"}
    assert client.find_group("BackROLL-Admins")["dn"] == ADMINS
    assert client.test() == {"base_dn": "DC=corp,DC=local"}
    client.close()


def test_the_real_client_reads_an_encrypted_password_of_the_service_account(mock_directory):
    config = mock_config()
    config.bind_password = vault.encrypt("svc-secret")
    client = mock_directory(config)
    assert client.find_user("alice").username == "alice"
    client.close()


def test_a_password_that_can_not_be_decrypted_is_an_error_of_the_directory_not_a_crash(mock_directory, monkeypatch):
    monkeypatch.setenv("SECRETS_KEY", "first-key")
    config = mock_config()
    config.bind_password = vault.encrypt("svc-secret")
    monkeypatch.setenv("SECRETS_KEY", "second-key")
    with pytest.raises(directory.DirectoryError, match="Type it again"):
        mock_directory(config).find_user("alice")


def test_the_real_client_reports_a_refused_service_account(mock_directory):
    config = mock_config()
    config.bind_password = "not the password"
    with pytest.raises(directory.DirectoryError, match="account that looks for the users"):
        mock_directory(config).find_user("alice")


def test_the_client_refuses_an_address_that_is_not_ldap():
    config = mock_config()
    config.server_url = "http://mock-dc"
    with pytest.raises(directory.DirectoryError, match="address of the directory"):
        directory.Ldap3Client(config).find_user("alice")
