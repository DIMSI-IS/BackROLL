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

Deployment architecture
-----------------------

.. figure:: https://i.ibb.co/nfCtLnX/archi.png
   :alt: Architecture schema

BackROLL deployment is fully integrated with docker-compose, greatly
reducing maintenance and installation/update procedures.

The application can be split with the following blocks:

-  CORE container, running the webserver that hosts the RESTful API
-  Workers that runs long running tasks (eg. backup / restore process)
   in the background
-  Scheduler which can add or delete scheduled (crontab format) tasks at
   runtime
-  Task manager UI/API to track and monitor all your tasks in the
   background
-  UI, to allow a simplified use of BackROLL

You can either choose to use the UI or/and the RESTful API.

Database and storage
--------------------

Information related to architecture
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A separated database is needed to store some information, like your
logical pools, your backup policies and hosts list. **No password is
stored in the database** as we choose to rely on an OpenID connector to
handle authentication. BackROLL also creates a SSH keypair during
installation to handle connection to hosts.

The access to the web interface is by default in HTTP only. We strongly
advise you to use a reverse-proxy (Nginx, Apache2, Haproxy, etc.) to
manage HTTPS.

Interfacing with KVM hosts and backup storage
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. figure:: https://i.ibb.co/2KhvTkQ/archi.png
   :alt: interfacing with KVM hosts schema

Backup storage must be directly accessible from a directory on the
server.

   Like /mnt/backup-storage1

This directory can be a mount point of NFS storage, local storage (not
recommended), etc.