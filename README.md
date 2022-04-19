![alt text](https://www.svgrepo.com/show/273645/storing-backup.svg =32x32?raw=true)
# BackROLL
|Version  | 0.1.0 |
|--|--|
| Website | https://backroll.readthedocs.io |



## What's BackROLL ?

BackROLL is modern, containerized and open-source backup solution for KVM guests.
It allows you to define logical KVM pools and backup policies to backup all your KVM guests according to your needs.

It's also

- A beautiful web UI to manage and monitor your backups, launch restore tasks, etc.
- No downtime during backups
- No agent on guests nor KVM hosts
- Fully containerized with minimum maintenance needed

## What do I need?
BackROLL 1.1.0 requires at least
- A MySQL/MariaDB database
- A server which can run Docker
- An OpenID provider (Keycloak, Google/Microsoft, Okta, etc.)

## Get Started

TBD

## Documentation
The [latest documentation](https://backroll.readthedocs.io/) is hosted at Read The Docs, containing user guides, tutorials, and an API reference.

## Help and support
We'd love to help you get started with BackROLL, so please feel free to open a case if you run into problems with the deployment or encounter bugs.

We are also looking for volunteers interested in the project to propose improvements, bug fixes or any other help that would be beneficial to this project.

## License

BackROLL Copyright (c) 2022 DIMSI Groupe

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation version 3 of the License.
This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program. If not, see  [http://www.gnu.org/licenses/](http://www.gnu.org/licenses/).

## Credits
BackROLL is based on several open-source projects (without any modification), including

-[BorgBackup](https://borgbackup.readthedocs.io/en/stable/index.html)
-[Celery](https://docs.celeryq.dev/en/stable/index.html)
-[FastAPI](https://fastapi.tiangolo.com)
-[Flower](https://flower.readthedocs.io/en/latest/)
-[RedBeat](https://github.com/sibson/redbeat)
-[REDIS](https://redis.io/)

Everything else is provided with ❤ by [DIMSI](https://www.dimsi.fr)
