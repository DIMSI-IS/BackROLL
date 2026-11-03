.. Licensed to the Apache Software Foundation (ASF) under one
   or more contributor license agreements.  See the NOTICE file
   distributed with this work for additional information#
   regarding copyright ownership.  The ASF licenses this file
   to you under the Apache License, Version 2.0 (the
   "License"); you may not use this file except in compliance
   with the License.  You may obtain a copy of the License at
   http://www.apache.org/licenses/LICENSE-2.0
   Unless required by applicable law or agreed to in writing,
   software distributed under the License is distributed on an
   "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
   KIND, either express or implied.  See the License for the
   specific language governing permissions and limitations
   under the License.

Host server configuration
"""""""""""""""""""""""""

There are 3 prerequisites to run BackROLL app, which are the following:

* Docker
* Docker-compose
* Git

The installer will automatically tell you if the installation conditions are complete or if any tools are missing or outdated.

All these packages can be easily installed with the APT tool.

Eg.

.. code-block:: bash

  apt install docker docker-compose git

Database preparation
""""""""""""""""""""

Database will be used to store some information, like hypervisors list, backup policies list, etc.

**The password of your users is never stored, only its bcrypt hash.** The few secrets that BackROLL must use itself (the API keys of the CloudStack connectors, the addresses of the Slack webhooks, the password of the Active Directory account) are stored encrypted.

You will need a Mysql/MariaDB database. This database can be hosted as another Docker image
(eg. `Installing and using MariaDB via docker <https://mariadb.com/kb/en/installing-and-using-mariadb-via-docker/>`_)

You can also use your existing server / cluster if you have one.

**Once your database has been created** and your user has been giving access, **keep information** such as Database server IP address, port, username/password and database name as you will need to fill them in the BackROLL configuration file.

When BackROLL starts, the application will check if database has been initialized. If this is not the case, the tables will be automatically created. So no action is required on the database side once connection has been set up.


Backup storage configuration
""""""""""""""""""""""""""""


Regardless of the choice of technology, the backup storage must be accessible from the server filesystem.
The easiest choice is an NFS share mounted directly on the host server.

`How to set up an NFS mount on Ubuntu 20.04 <https://www.digitalocean.com/community/tutorials/how-to-set-up-an-nfs-mount-on-ubuntu-20-04>`_

.. note::

  As of version 0.1.0, two shares have to be set up in BackROLL.
  These two shares must be in the /mnt/ directory**

Example:

* **/mnt/share1**
* **/mnt/share2**

The ability to declare as many shares as desired is planned for a future version. Stay tuned !

Users and roles
"""""""""""""""

BackROLL manages its own users, in its database. No identity provider is needed.

The first time the UI is opened, it asks for the administrator account. Then the administrator creates the other users in *Parameters > Users*, with one of these roles:

* **viewer**: reads everything, changes nothing.
* **editor**: also creates, updates and deletes resources, and starts backups and restores.
* **admin**: also manages the users and reads the audit log.

The login tokens are signed with the secret ``JWT_SECRET``, which must be at least 32 random characters.

Running BackROLL
""""""""""""""""

BackROLL is a Docker Compose project. Get the release you target with git, then use the helper script of the compose project. It asks for the database, the Flower account and the address of the UI, generates the secret of the login tokens (``JWT_SECRET``) and writes the configuration:

.. code-block:: bash

  git clone https://github.com/DIMSI-IS/BackROLL.git
  cd BackROLL/compose_project
  source source-me.sh setup-prod
  docker compose $prod up -d

The ``prod`` mode downloads the Docker images of the release from Docker Hub: they have to be published first. To try a version whose images are not published, build them from the source with the ``staging`` mode instead (``source source-me.sh setup-staging``, then ``docker compose $staging up -d``).

The first start of the database takes about a minute. Then open the address of the host in a web browser (port 80): the first time, BackROLL asks you to create the administrator account.

The secrets that BackROLL keeps in its database (the API keys of the connectors, the addresses of the Slack webhooks, the password of the Active Directory account) are encrypted with the key ``SECRETS_KEY``, or with ``JWT_SECRET`` when it is not set. If that key changes, those values have to be typed again.

The setup generates the two keys apart: ``SECRETS_KEY`` for the secrets and ``JWT_SECRET`` for the login tokens. Save the file ``compose_project/@prod.env`` with the backups of the database: without it the saved secrets can not be read. Run the setup only once: when the file already exists the script refuses to go on, because new keys would make the saved secrets unreadable. To update, get the new version with git and recreate the containers (``docker compose $prod up -d``).

Flower, the monitoring of the tasks, only listens on the host itself (``127.0.0.1:5555``): use an SSH tunnel to reach it from another machine.

See `the compose project README <https://github.com/DIMSI-IS/BackROLL/blob/main/compose_project/README.md>`_ for the other modes and the commands.

Securing endpoints
^^^^^^^^^^^^^^^^^^

As you may have noticed, these endpoints are HTTP only.

You can put BackROLL behind a proxy/reverse-proxy to access it in HTTPS mode with domain resolution.
This will allows you to do SSL Termination on the reverse-proxy side.

`eg. NGINX SSL Termination <https://docs.nginx.com/nginx/admin-guide/security-controls/terminating-ssl-http/>`_

If the UI is reached through another address than ``FRONT_URL``, add it to ``CORS_ORIGINS``.
