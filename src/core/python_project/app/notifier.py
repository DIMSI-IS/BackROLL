"""A message to an external hook (Slack), for the events that are not the end of a backup task: the end of a
disaster recovery, a disk that needs attention. The messages of the backups themselves are in app/hooks.

Everything here is best effort: a hook that does not answer never stops a restore or a backup.
"""

from datetime import datetime
from uuid import UUID

from sqlmodel import Session

from app import vault
from app.database import ExternalHooks, init_db_connection
from app.environment import get_env_var


def front_url(path: str) -> str:
    """A link to the interface, empty when its address is not known."""
    try:
        return f"{get_env_var('FRONT_URL').rstrip('/')}/{path.lstrip('/')}"
    except Exception:
        return ""


def send(hook_id: UUID | str | None, text: str, blocks: list | None = None) -> bool:
    """True when the hook took the message. The callers that do not care for the answer ignore it."""
    if not hook_id:
        return False
    try:
        from slack_sdk.webhook import WebhookClient
        with Session(init_db_connection()) as session:
            hook = session.get(ExternalHooks, UUID(str(hook_id)))
        if hook:
            WebhookClient(vault.decrypt(hook.value)).send(text=text, **({'blocks': blocks} if blocks else {}))
            return True
    except Exception as exception:
        print(f"Unable to notify the external hook. {exception}")
    return False


def send_to_policy_hook(virtual_machine: dict, text: str, blocks: list | None = None):
    """To the hook of the backup policy of the machine, if its policy has one."""
    try:
        from app import policy_lookup
        send(policy_lookup.policy_of(virtual_machine).externalhook, text, blocks)
    except Exception as exception:
        print(f"Unable to find the hook of the policy of the machine. {exception}")


def attention_message(vm_name: str, disk: str, reason: str) -> str:
    link = front_url("admin/dashboard")
    return (f"<!channel> :warning: *The backups of {vm_name} are stopped*\n"
            f"Disk `{disk}` needs attention: {reason}\n"
            "Check the disks of the machine on the hypervisor, then resume its backups from the dashboard."
            + (f" {link}" if link else ""))


def storage_space_message(storage_name: str, percent: float, free: int, total: int, limit: int) -> str:
    return (f"<!channel> :warning: *The backup storage {storage_name} is {percent:.0f} % full*\n"
            f"{human_size(free)} free of {human_size(total)}. The alert limit is {limit} %. "
            "New backups need free space: clean the old backups or extend the storage.")


def host_problem_lines(problems: list, bold: bool = False) -> str:
    return "\n".join(f"• {'*' if bold else ''}{host}{'*' if bold else ''}: {reason}" for host, reason in problems)


def host_problem_outcome(cancelled: bool) -> str:
    return ("The backups of the whole pool did not start." if cancelled
            else "The machines of the other hypervisors are backed up.")


def host_problem_message(pool_name: str, problems: list, cancelled: bool = False) -> str:
    """The hypervisors of a pool whose machines could not be backed up, with the reason of each."""
    return (f"<!channel> :warning: *Backups not made in the pool {pool_name}*\n"
            f"{host_problem_lines(problems)}\n{host_problem_outcome(cancelled)}")


def drp_finished_message(request: dict, vm_id: str | None) -> str:
    where = f" for the account {request['account']}" if request.get("account") else ""
    return (f":white_check_mark: *Disaster recovery restore finished*\n"
            f"New virtual machine *{request['name']}*{where}, restored from `{request['repository']}` "
            f"({len(request['disks'])} disk(s))." + (f" CloudStack id `{vm_id}`." if vm_id else ""))


def drp_failed_message(request: dict, error: str) -> str:
    return (f"<!channel> :x: *Disaster recovery restore failed*\n"
            f"New virtual machine *{request['name']}*, from `{request['repository']}`: {error}")


# -- the cards ---------------------------------------------------------------------------------------------------
# The same look as the summary of a pool: a title, the facts in two columns, the detail, a button, a footer. The
# plain text of each message is kept: it is what Slack shows in a notification, and where blocks are not shown.

def human_size(size: int) -> str:
    value = float(size or 0)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if value < 1024 or unit == "TiB":
            return f"{int(value)} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024


def card(title: str, fields=(), details: str | None = None, mention: bool = False, button: tuple | None = None) -> list:
    blocks = [{"type": "header", "text": {"type": "plain_text", "text": title[:150], "emoji": True}}]
    if mention:
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": "<!channel> *Action needed*"}})
    shown = [{"type": "mrkdwn", "text": f"*{label}*\n{value}"} for label, value in fields if value not in (None, "")]
    if shown:
        blocks.append({"type": "section", "fields": shown[:10]})
    if details:
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": details[:2500]}})
    if button and button[1]:
        blocks.append({"type": "actions", "elements": [{
            "type": "button", "text": {"type": "plain_text", "text": button[0]}, "url": button[1]}]})
    blocks.append({"type": "context", "elements": [{
        "type": "mrkdwn", "text": f"BackROLL · {datetime.now().strftime('%Y-%m-%d %H:%M')}"}]})
    return blocks


def storage_space_blocks(storage_name: str, percent: float, free: int, total: int, limit: int) -> list:
    return card(
        f":warning: Backup storage almost full: {storage_name}",
        [("Storage", storage_name), ("Used", f"{percent:.0f} %"), ("Free", human_size(free)),
         ("Total", human_size(total)), ("Alert limit", f"{limit} %")],
        "*What to do*\nNew backups need free space. Clean the old backups (Tasks > Clean backup) or extend the storage.",
        mention=True, button=("Open the dashboard", front_url("admin/dashboard")))


def attention_blocks(vm_name: str, disk: str, reason: str) -> list:
    return card(
        f":warning: Backups stopped: {vm_name}",
        [("Machine", vm_name), ("Disk", f"`{disk}`"), ("Status", "Needs attention")],
        f"*Reason*\n>{reason}\n*What to do*\nCheck the disks of the machine on the hypervisor "
        f"(`virsh domblklist {vm_name}`), then resume its backups from the dashboard.",
        mention=True, button=("Open the dashboard", front_url("admin/dashboard")))


def host_problem_blocks(pool_name: str, problems: list, cancelled: bool = False) -> list:
    return card(
        f":warning: Backups not made in the pool {pool_name}",
        [("Pool", pool_name), ("Hypervisors", str(len(problems)))],
        f"*Reason*\n{host_problem_lines(problems, bold=True)}\n*What to do*\nCheck that the hypervisor runs, answers on "
        f"port 22 (SSH) and is connected in BackROLL (Hosts page). {host_problem_outcome(cancelled)}",
        mention=True, button=("Open the dashboard", front_url("admin/dashboard")))


def drp_finished_blocks(request: dict, vm_id: str | None) -> list:
    return card(
        ":white_check_mark: Disaster recovery restore finished",
        [("New virtual machine", request["name"]), ("Restored from", f"`{request['repository']}`"),
         ("Disks", str(len(request["disks"]))), ("Account", request.get("account")),
         ("CloudStack id", f"`{vm_id}`" if vm_id else None)],
        button=("Open the restores", front_url("admin/tasks/drp")))


def drp_failed_blocks(request: dict, error: str) -> list:
    return card(
        ":x: Disaster recovery restore failed",
        [("New virtual machine", request["name"]), ("Restored from", f"`{request['repository']}`")],
        f"*Error*\n```{error[:1800]}```", mention=True, button=("Open the restores", front_url("admin/tasks/drp")))


CLEANING_KINDS = {"old": "Old backups", "deleted": "Backups of deleted machines"}


def cleaning_started_blocks(storage_name: str, kind: str) -> list:
    return card(":broom: Cleaning started", [("Storage", storage_name), ("What", CLEANING_KINDS[kind])])


def cleaning_finished_blocks(storage_name: str, kind: str, status: str, summary: dict) -> list:
    failed = status != "success"
    return card(
        ":x: Cleaning failed" if failed else ":white_check_mark: Cleaning finished",
        [("Storage", storage_name), ("What", CLEANING_KINDS[kind]),
         ("Backups deleted", str(summary.get("archives_deleted", 0))),
         ("Repositories", str(summary.get("repositories", 0))),
         ("Space freed", human_size(summary.get("freed_bytes", 0))),
         ("Errors", str(summary.get("errors", 0)))],
        "The log of the run is in BackROLL, with the details of each repository." if failed else None,
        mention=failed, button=("Open the cleaning", front_url("admin/tasks/cleanup")))


def example_messages() -> list:
    """One example of each message that BackROLL posts outside the end of a backup, for the test of a hook."""
    request = {"name": "restored-vm", "repository": "i-2-17543-VM", "disks": ["ROOT-17543_x_1", "DATA-2_y_1"], "account": "drp-test"}
    summary = {"repositories": 3, "archives_deleted": 12, "freed_bytes": 5 * 1024 ** 3, "errors": 0}
    return [
        ("Backups stopped", attention_blocks(
            "i-535-18737-VM", "vdb", "vdb: the machine already writes in an overlay (/mnt/pool/vol-1.snap)")),
        ("Disaster recovery restore finished", drp_finished_blocks(request, "5b1c0b7e-0000-0000-0000-000000000001")),
        ("Disaster recovery restore failed", drp_failed_blocks(
            request, "No primary storage is mounted: the restored disks could not be copied.")),
        ("Cleaning started", cleaning_started_blocks("BACKUP_STORAGE", "old")),
        ("Cleaning finished", cleaning_finished_blocks("BACKUP_STORAGE", "old", "success", summary)),
        ("Deletion of the backups of deleted machines finished", cleaning_finished_blocks(
            "BACKUP_STORAGE", "deleted", "success", {**summary, "freed_bytes": 2 * 1024 ** 4 + 300 * 1024 ** 3})),
        ("Cleaning failed", cleaning_finished_blocks("BACKUP_STORAGE", "old", "failed", {**summary, "errors": 1})),
        ("Backup storage almost full", storage_space_blocks(
            "BACKUP_STORAGE", 87.0, 190 * 1024 ** 3, 1500 * 1024 ** 3, 85)),
    ]


EXAMPLE_MARK = {"type": "context", "elements": [{
    "type": "mrkdwn", "text": ":eyes: *TEST* : message of the test of the hook, nothing to do"}]}


def send_examples(hook_id) -> int:
    """Posts the examples to the hook. Returns how many were sent."""
    import time
    count = 0
    for text, blocks in example_messages():
        send(hook_id, f"[TEST] {text}", [EXAMPLE_MARK] + blocks)
        count += 1
        time.sleep(1)
    return count
