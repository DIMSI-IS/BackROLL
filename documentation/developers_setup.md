# Backroll developers’ setup

Here is our recommended developers’ setup to contribute to Backroll.

## WSL

If you are on Windows, you can work on linux throught [WSL](https://learn.microsoft.com/fr-fr/windows/wsl/install).

## Docker

### Windows & Linux desktops

If you want to work locally, install [Docker Desktop](https://docs.docker.com/desktop/install/windows-install/).

### Linux server

If you plan to work remotely on a linux server :

- install [Docker](https://docs.docker.com/engine/install/)
- install [Docker Compose](https://docs.docker.com/compose/install/linux/)

## Visual Studio Code

Install [Visual Studio Code](https://code.visualstudio.com/download).

### Extensions

#### Windows

If you are on Windowns, install the [WSL extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-wsl). Connect to WSL with Visual Studio Code before cloning the Backroll repository.

#### Remote developement

If you plan to work remotely on a server, install the remote connexion extensions :

- [Remote - SSH](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-ssh)
- [Remote - SSH: Editing Configuration Files](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-ssh-edit)
- [Remote Explorer](https://marketplace.visualstudio.com/items?itemName=ms-vscode.remote-explorer)

#### Docker

You can install the [Docker extension](https://marketplace.visualstudio.com/items?itemName=ms-azuretools.vscode-docker). It provides a UI to manage containers and other Docker stuff directly into Visual Studio Code. However, it may no guess the full docker compose command you used to set up your containers, so just fallback to the command line.

## KVM

To contribute to Backroll, you will need to have an hypervisor and some VMS to play with.

So let’s setup KVM :

- start with this [beginners’ guide](https://ubuntu.com/blog/kvm-hyphervisor)
- if libvirtd is not running, see this [thread](https://askubuntu.com/questions/1225216/failed-to-connect-socket-to-var-run-libvirt-libvirt-sock#answers)

Then create a VM :

- see this [thread](https://unix.stackexchange.com/questions/309788/how-to-create-a-vm-from-scratch-with-virsh). `virt-manager` is a nice tool.

If Backroll and KVM are running on the same host (WSL or a linux computer), you can reach the hypervisor by using the special domain name `host.docker.internal`.
