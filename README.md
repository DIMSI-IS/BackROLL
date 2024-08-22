[![Documentation Status](https://readthedocs.org/projects/backroll/badge/?version=latest)](https://backroll.readthedocs.io/en/latest/?badge=latest)

## <img src="https://user-images.githubusercontent.com/49555363/194335646-85c5513e-cceb-4cc5-99f7-406c7a987156.svg" height="32px">

Latest version  | 0.3.0
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

## Our demo made during the CloudStack European User Group (APRIL) 2022
[![Watch the video](http://i3.ytimg.com/vi/Jg40h1YjALk/hqdefault.jpg)](https://www.youtube.com/watch?v=Jg40h1YjALk)
  
## What do I need?
BackROLL 0.3.0 requires at least
- A server which can run Docker
- A MySQL/MariaDB database ( the default configuration deploys a mariaDB with docker compose )
- An OpenID provider (Keycloak, Google/Microsoft, Okta, etc.)

## Get Started
### Docker and Docker compose
Backroll requires Docker and Docker Compose. Please refer to the official Docker documentation to install them.\
- Install Docker https://docs.docker.com/engine/install/ 
- Install Docker compose https://docs.docker.com/compose/install/linux/

### Quick install
This method uses a preconfigured oauth provider in docker, for production environment please use your production oauth provider or harden the preconfigured oauth provider with SSL certificate, secure password, etc..

Download the install-prod.sh script
```bash
wget https://github.com/DIMSI-IS/BackROLL/releases/download/v.0.3.0/install-prod.sh
```
Allow the script execution
```bash
sudo chmod +x install-prod.sh
```
Start the script
```bash
sudo ./install-prod.sh
```
Change directory to the backroll install directory
```bash
cd your_backroll_path/install/
```
Start the docker-compose.yml, this will start all the containers.
```bash
sudo docker compose up -d
```
Verify that your container are running
```bash
sudo docker ps
```

## Backroll Configuration
### Storage configuration
To perform backup and restore tasks, Backroll's workers need an access to the VMs storage and to a backup storage. \
By default in the docker-compose.yml, /mnt/ is mapped to /mnt/ in the workers.


#### VM Storage configuration
On the backroll VM, mount the VMs storage to a path that is mapped in docker-compose.yml.
If you are mounting a Cloudstack Primary storage please respect the Cloudstack format such as: /mnt/PR_STORAGE_ID
Repeat for each VM storage.

Example using a NFS storage:

```bash
# Create directory under /mnt/
mkdir /mnt/myVM_storage

# Mount using NFS, to make the mount persistent, edit fstab with corresponding values
mount -v -t nfs -o nolock NFS_server:/nfs_share1 /mnt/myVM_storage

```
Example using a Cloudstack NFS storage:

```bash
#If you are mounting a Cloudstack Primary storage please respect the Cloudstack format such as: /mnt/PR_STORAGE_ID
# Create directory under /mnt/ corresponding to your CS primary storage
mkdir /mnt/138338fb-xxxx-xxxx-b219-ff968ca3ed3d

# Mount using NFS, to make the mount persistent, edit fstab with corresponding values
mount -v -t nfs -o nolock NFS_server:/nfs_shareCS1 /mnt/138338fb-xxxx-xxxx-b219-ff968ca3ed3d

```

#### Backup Storage configuration
On the backroll VM, mount the backup storage to a path that is mapped in docker-compose.yml.\
Then in Backroll UI, Configuration > Storage > Add new storage > Input Name and the path > Validate\

Example using a NFS storage:


```bash
# Create directory under /mnt/
mkdir /mnt/backup_storage

# Mount using NFS, to make the mount persistent, edit fstab with corresponding values
mount -v -t nfs -o nolock NFS_server:/nfs_backup_share1 /mnt/backup_storage

Then add your storage in the Backroll UI.

```


## Backroll with Cloudstack
### Configure the Backroll Plugin

**Cloudstack Global Settings**\
In Cloudstack's Global settings, fill the fields with the appropriate value:

- Backup framework provider plugin: _backroll_
- Backup plugin backroll config appname: _Name of your app name used for backroll api_
- Backup plugin backroll config password: _Secret for the backroll_api found in your oauth provider._
- Backup plugin backroll config url: _URL of your backroll_


**Cloudstack user**\
Backroll uses an API key and secret to communicate with Cloudstack.\
In Cloudstack, under accounts, create a user dedicated to backroll.\
Generate API Keys and Secret.


**Backroll side**\
In the backroll UI, under Configuration select Connectors.\
Add a new connector and fill the field with the appropriate information:

- Name: *Name of your connector*
- Endpoint URL: *URL of your cloudstack instance*
- Login: *API_key of your user dedicated to backroll*
- Password: *API_secret of your user dedicated to backroll*


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
