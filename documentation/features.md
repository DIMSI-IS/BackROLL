# Features of this version of BackROLL

The *Documentation* page of the interface describes every option, in English and French. This file is the short version, for developers.

## Users and roles

BackROLL stores its own users, with a bcrypt hash of their password.

| Role | Can do |
|---|---|
| viewer | read everything |
| editor | viewer + create, update and delete resources, start backups and restores, browse and download the files of a backup, run a disaster recovery |
| admin | editor + manage the users, read the audit log |

- **First start**: the UI asks for the administrator account while no user exists. There is no default account.
- **Users page** (*Parameters > Users*, admins): create a user, change a role, disable, reset a password, unlock, delete. An admin cannot demote, disable or delete themselves.
- **Login protection**: after 5 failed logins in a row an account is locked for 15 minutes, even for the right password. An admin unlocks it from the users page, and a password reset unlocks it too.
- **Tokens**: JSON Web Tokens signed with `JWT_SECRET`, valid `JWT_LIFETIME_MINUTES` (480 by default). A role change, a deactivation or a password change applies at once.
- **CloudStack plugin**: `POST /api/v1/auth/cloudstack/login` authenticates as a local user, whose role limits what CloudStack can do.

## Audit log

*Parameters > Audit log* (admins) lists every change made through the API: who, what, the result, the address, and details such as the role given to a user. Failed logins and denied requests are recorded. Reads are not, except the download of a file from a backup. Passwords are never recorded.

## Active Directory

Optional. The users of the company log in with their Active Directory account, and a role is given to each group (*Parameters > Active Directory*).

- The password is checked by the directory itself and never kept. The role is worked out again at each login: the highest role of the groups of the list, nested groups included. A user in none of the groups cannot log in.
- A local user with the same name always wins, and the local users keep working when the directory is down.
- A disabled account is refused. The failed logins are counted apart from the directory, so that BackROLL cannot be used to lock the accounts of the company.
- Every login through the directory is in the audit log with the source *Active Directory*.

## Slack notifications

Hooks (*Configuration > External hooks*) post cards in Slack: the end of a single backup, the summary of a pool (successes, failures, skipped, blocked), the restore of a disk, a disaster recovery, a disk that needs attention, a cleaning (start, end, failure), a backup storage that is almost full (limit in Settings, checked every 15 minutes, one message each time it is crossed) and the hypervisors of a pool that were not backed up (no answer on port 22, not connected, machines that could not be listed). The test button posts an example of every message.

## Secrets

The address of the Slack webhooks, the secret key of the CloudStack connectors and the password of the Active Directory account are encrypted in the database (Fernet, key `SECRETS_KEY`, or `JWT_SECRET` when it is not set). Values written before are still read and are encrypted at the next start. They are never sent back to the browser. If the key changes, they have to be typed again.

A secret that can no longer be read (the key changed, for instance after a reinstall without `@prod.env`) is told with a 409 and the sentence "type it again in the settings"; the lists stay usable with the value hidden. The setup (`source-me.sh setup-prod`) generates `SECRETS_KEY` apart from `JWT_SECRET`, and refuses to run again when `@prod.env` exists, because new keys would make the saved secrets unreadable: keep that file with the backups of the database.

A connector that does not answer (unreadable secret, wrong credentials, timeout) no longer drops its machines in silence: the machines of the hypervisors are listed, and a warning on the dashboard and on the list of machines says that the machines that only CloudStack knows are missing (`GET /api/v1/virtualmachines/warnings`).

## Machines that are not running, and locks

A machine that is stopped, off or changing state is not backed up: its task ends as *skipped* (orange badge, the reason in the hint), nothing is copied, no failure is notified. A backup and a restore never run together on a machine: one lock per machine, taken with a single Redis command (`SET NX EX`), the same for both.

## Safety of the inputs and of the restores

- The address of a host, the path of a storage and the name of a backup are checked where they come in, and quoted where they reach a shell command.
- A restore refuses a backup that matches none of the disks of the machine, checks the free space where the disk is replaced before stopping the machine, and starts the machine again if it fails. A backup of folders and files cannot be used to restore a disk.
- After each retention (policy or cleaning), `borg compact` frees the space of the deleted backups.

## Backup files

On the page of a virtual machine, *Backup(s)*, the folder button opens the files of a backup.

1. The disk of the backup is extracted once, in `<backup storage>/restore/.file-browser/`.
2. It is read with libguestfs, without being mounted on the host.
3. Folders are browsed, a file is downloaded as is, a folder as a `.tar`.
4. *Close*, or 30 minutes (`FILE_BROWSER_TTL_MINUTES`) without use, deletes the copy.

CloudStack disks that have a backing file are handled: the saved copy of the template is used, read only. libguestfs is much faster when the backend container has `/dev/kvm`.

## Folders and files in the policy

A backup policy can list folders and files of the virtual machines (one absolute path per line, 20 at most). Each backup of a virtual machine also backs them up, before the disks:

- every path is read in the disks with libguestfs, without mounting them, and stored by Borg in its own archive named `files_<path>_<date>` in the repository of the virtual machine;
- an unchanged folder costs almost nothing, as Borg deduplicates it, and the archives follow the retention of the policy;
- a path that cannot be read (it does not exist, for instance) is reported in the log of the task. The other paths and the disks are backed up anyway;
- these archives are browsed and downloaded like the files of a disk, from the backup list of the virtual machine (they are labelled FILES). They cannot be used for a full disk restore or for the disaster recovery.

## Settings

*Parameters > Settings* (administrators) changes, without a restart, what used to be set with environment variables:

| Setting | Default | Environment variable it replaces |
|---|---|---|
| Virtual machines backed up at the same time | 2 | none (at most `BACKUP_MAX_CONCURRENCY`) |
| Alert when the disk of a backup storage is almost full | 85 % | none |
| Keep the history of the backups and restores | 90 days | `TASK_HISTORY_RETENTION_DAYS` |
| Keep the audit log | 365 days | `AUDIT_RETENTION_DAYS` |
| Keep a copy opened to browse a backup | 30 minutes | `FILE_BROWSER_TTL_MINUTES` |
| Length of a login session | 480 minutes | `JWT_LIFETIME_MINUTES` |
| Failed logins before a lock | 5 | `LOGIN_MAX_ATTEMPTS` |
| Length of the lock | 15 minutes | `LOGIN_LOCK_MINUTES` |

A value saved in the page wins; without one, the environment variable is the default, then the value above. A change applies at once. The other backups wait for a free place, in the order they were started, also when the number of simultaneous backups changes. Old audit entries and old task records are deleted by a cleaning that runs at start and every six hours. Changes are recorded in the audit log.

## Dashboard, refresh and documentation

- The dashboard shows the backups running and waiting, the successes and failures of the last 24 hours, the latest failures, and the next scheduled backups.
- *Protection* counts the machines that are protected, at risk (last backup older than 24 h, 48 h, 7 days or 30 days) or never backed up. It reads the Borg repositories (`GET /api/v1/dashboard/protection`, kept one minute). The archives of folders and files do not count as a backup of the machine.
- The top bar has a refresh button and the period of the automatic refresh (off, 5 s, 10 s, 30 s, 1 min), kept in the browser. Nothing is reloaded while the tab is hidden, nor the resource lists while a form is open.
- The *Documentation* page of the interface describes every option, with a search.

## History of the backups and restores

*Tasks > Backup* and *Tasks > Restore* list the backups and restores with their state. Flower, which feeds these lists, keeps them in memory and loses them each time its container is recreated, so the worker also records every backup and restore in the database when it starts and ends (the machine, the start, the duration, the result and the error). The lists show both, and the dashboard counters use them. Records older than `TASK_HISTORY_RETENTION_DAYS` (90) are deleted when the API starts. A backup that waits for a free place is already recorded as running.

## Clean backup

*Tasks > Clean backup* replaces the shell scripts that ran `borg prune --keep-daily=30` on every repository of a storage, and that removed by hand the repositories of deleted machines. Everything is set per backup storage:

- **Keep one backup per day for the last N days** (30 by default, 1 to 3650). Every kind of archive of a repository (`vda`, `vdb`, `hda`, `files`, ...) is cleaned apart, like the script did for each disk prefix. Borg counts the days that have a backup. The weekly and monthly retention of the backup policies is not taken into account: older backups are deleted. The space is then freed (`borg compact`).
- **Clean right after a backup**: the repository of the machine that was just backed up is cleaned. A cleaning that deleted nothing is not recorded.
- **Clean on a schedule**: every day or every week at a time, or a cron expression. A cleaning that is already running is not started twice.
- **Run now**, with a confirmation. It uses the saved number of days.
- **Simulation**: shows what a cleaning would delete, machine by machine, and deletes nothing. Everything is ticked; the administrator unticks what to keep, then deletes the selection after typing the confirmation word. The server computes the list again when it deletes, and refuses a backup that the rule keeps. A backup left unticked is only kept until another cleaning applies the rule.
- An optional **external hook** (Slack) is told when a cleaning starts, ends or fails.
- **Backups of machines that no longer exist**: *Look for them* compares the repositories of a storage with the machines of all the hypervisors and connectors. Nothing is selected by default; deleting needs a typed confirmation, and BackROLL checks again at that moment that each machine is gone. The search refuses to answer when a hypervisor is unreachable or not connected, or when no machine is found, because every repository would look abandoned. Only real Borg repositories of the storage are deleted, and not the ones in use.
- **History**: every cleaning is recorded with its summary (backups deleted, repositories, space freed, errors) and its full log, for administrators to read in the page.

Only administrators change the settings and start a cleaning. Each action is in the audit log.

## Disaster recovery

*Tasks > Disaster recovery* restores a backed up VM into a **new** CloudStack VM, in the same environment or another one, for the account of any domain.

1. Choose the backup storage, the VM, and the backup of each disk (the root disk first).
2. Choose the CloudStack connector, then optionally a domain and an account (the templates and networks offered are the ones of that account), the zone, the compute offering, the template (only used to create the VM), the network and an IP address.
3. BackROLL extracts the disks, merges the backing file into them, creates the VM, then copies the disks over its volumes.

Requirements: the primary storage of the target must be mounted in the BackROLL containers as `/mnt/<storage pool id>`, writable. If a network is not chosen and the account has several, CloudStack refuses: the page then requires the choice. *Delete the new VM if the restore fails* removes only the machine this restore created.

The page lists the **history** of the restores: user, source, target, new VM, steps, result and error. A restore still marked as running after 12 hours is shown as failed when the API starts.

A virtual machine restored from a backup is a new machine for cloud-init, which locks the password of the default user of the image. SSH keys and the data are restored.

## Environment variables

| Variable | Default | Role |
|---|---|---|
| `JWT_SECRET` | none, required | signs the login tokens, at least 32 characters |
| `SECRETS_KEY` | `JWT_SECRET` | key that encrypts the secrets kept in the database |
| `JWT_LIFETIME_MINUTES` | 480 | life of a token |
| `LOGIN_MAX_ATTEMPTS` | 5 | failed logins before the lock |
| `LOGIN_LOCK_MINUTES` | 15 | length of the lock |
| `AUDIT_RETENTION_DAYS` | 365 | audit entries older than that are deleted at startup |
| `BACKUP_MAX_CONCURRENCY` | 8 | processes of the backup worker, the highest number of simultaneous backups that can be chosen in Settings (set it in `compose_project/@<mode>.env`, then restart `worker_secondary`) |
| `TASK_HISTORY_RETENTION_DAYS` | 90 | age after which the history of the backups and restores is deleted |
| `FILE_BROWSER_TTL_MINUTES` | 30 | life of the copy opened to browse a backup |
| `CORS_ORIGINS` | `FRONT_URL` | sites allowed to call the API from a browser, separated by commas |
| `SQLITE_DIRECTORY` | none | forces an SQLite database in that folder, used by the tests |

## Tests

```bash
cd src/core/python_project
pytest tests
```

The tests use a temporary SQLite database, never a real one. Those that need Borg, QEMU, libguestfs or libvirt are skipped where they are missing: run the whole suite in the backend container.

The interface has its own tests, in a real browser, on the built interface with a demo backend (`src/ui/tests/e2e`, see `CONTRIBUTING.md`). The CI (GitHub Actions) runs both on every push.
