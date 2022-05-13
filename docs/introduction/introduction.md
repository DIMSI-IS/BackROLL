# Introduction

## What is BackROLL ?

BackROLL is modern, containerized and open-source backup web application for KVM guests. It allows you to define logical KVM pools and backup policies to backup all your KVM guests according to your needs.

It's also

-   A beautiful web UI to manage and monitor your backups, launch restore tasks, etc.
-   No downtime during backups
-   No agent on guests nor KVM hosts
-   Fully containerized with minimum maintenance needed

## What can BackROLL do ?

- Define, schedule and monitor your backup tasks from a single web app
- Browse all virtual machines running on your hosts
- Browse their backups and launch fully automated restore tasks or backup tasks
- Manually launch backups tasks on single virtual machine or on a pool
- Incremental backup and retention policy mechanism included to save disk space

## Architecture review

![Architecture](https://i.ibb.co/nfCtLnX/archi.png)

BackROLL deployment is fully integrated with docker-compose, greatly reducing maintenance and installation/update procedures.

The application can be split with the following blocks:

- CORE container, running the webserver that hosts the RESTful API
- Workers that runs long running tasks (eg. backup / restore process) in the background
- Scheduler which can add or delete scheduled (crontab format) tasks at runtime
- Task manager UI/API to track and monitor all your tasks in the background
- UI, to allow a simplified use of BackROLL

You can either choose to use the UI or/and the RESTful API.

### Information related to architecture

A separated database is needed to store some information, like your logical pools, your backup policies and hosts list.
**No password is stored in the database** as we choose to rely on an OpenID connector to handle authentication. BackROLL also creates a SSH keypair during installation to handle connection to hosts.

The access to the web interface is by default in HTTP only. We strongly advise you to use a reverse-proxy (Nginx, Apache2, Haproxy, etc.) to manage HTTPS.

### Interfacing with KVM hosts and backup storage

![enter image description here](https://i.ibb.co/2KhvTkQ/archi.png)

Backup storage must be directly accessible from a directory on the server.

> Like /mnt/backup-storage1

 This directory can be a mount point of NFS storage, local storage (not recommended), etc.