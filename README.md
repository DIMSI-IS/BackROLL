[![Documentation Status](https://readthedocs.org/projects/backroll/badge/?version=latest)](https://backroll.readthedocs.io/en/latest/?badge=latest)

## <img src="https://user-images.githubusercontent.com/49555363/194335646-85c5513e-cceb-4cc5-99f7-406c7a987156.svg" height="32px">

Latest version  | 0.1.0
------------- | -------------
Documentation  | https://backroll.readthedocs.io

## What's BackROLL ?

BackROLL is modern, containerized and open-source backup solution for KVM guests.
It allows you to define logical KVM pools and backup policies to backup all your KVM guests according to your needs.

It's also

- A beautiful web UI to manage and monitor your backups, launch restore tasks, etc.
- No downtime during backups
- No agent on guests nor KVM hosts
- Fully containerized with minimum maintenance needed

## Our demo made during the CloudSTack European User Group (APRIL) 2022
[![Watch the video](http://i3.ytimg.com/vi/Jg40h1YjALk/hqdefault.jpg)](https://www.youtube.com/watch?v=Jg40h1YjALk)
  
## What do I need?
BackROLL 0.1.0 requires at least
- A MySQL/MariaDB database
- A server which can run Docker
- An OpenID provider (Keycloak, Google/Microsoft, Okta, etc.)

## Get Started

### As a developer

To start working on the BackROLL project, use the [development setup](./backroll-dev/README.md).

### As an user

Coming soon... :smirk:

## Documentation
The [latest documentation](https://backroll.readthedocs.io/) is hosted at Read The Docs, containing user guides, tutorials, and an API reference.

## Help and support
We'd love to help you get started with BackROLL, so please feel free to open a case if you run into problems with the deployment or encounter bugs.

We are also looking for volunteers interested in the project to propose improvements, bug fixes or any other help that would be beneficial to this project.

## License

Licensed to the Apache Software Foundation (ASF) under one or more contributor license agreements. See the NOTICE file distributed with this work for additional information regarding copyright ownership. The ASF licenses this file to you under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.

Please see the [LICENCE](https://github.com/DIMSI-IS/BackROLL/blob/main/LICENCE) file included in the root directory of the source tree for extended license details.

## Credits
BackROLL is based on several open-source projects (without any modification), including

* [BorgBackup](https://borgbackup.readthedocs.io/en/stable/index.html)
* [Celery](https://docs.celeryq.dev/en/stable/index.html)
* [FastAPI](https://fastapi.tiangolo.com)
* [Flower](https://flower.readthedocs.io/en/latest/)
* [RedBeat](https://github.com/sibson/redbeat)
* [REDIS](https://redis.io/)

Everything else is provided with ❤ by [DIMSI](https://www.dimsi.fr)
