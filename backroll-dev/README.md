# Development setup

This docker compose project provides a development version of backroll. The only component that is not included is the KVM host. The project is already set up with a sample configuration.

## First start
TODO ssh keys

You need to start the docker compose project:

1. Be shure that you are in the right directory:

```bash
cd backroll-dev
```

2. Start the project with docker compose by specifing a local ip address:

```bash
HOST_IP=local.ip.address docker compose up
```

- `HOST_IP` is required to make the SSO work.
- The IP address must be accessible from the host and from the containers.
- On Windows, you can use the host IP in the "Hyper-V Virtual Ethernet Adapter" network made for WSL. This is a good choice since it is a static IP.

The first start is longer than the next ones due to image building and containers’ initialisation.

## Next starts

For the next starts, you may omit the `HOST_IP`:
```bash
cd backroll-dev
docker compose start
```

Or else you can use the Docker Desktop UI, the Docker extension for Visual Studio Code or any other Docker UI.

If you need to recreate a container with the `create` or the `up` compose commands, you must specify `HOST_IP` again.

## User interface

You can access BackROLL at the following address:

- [http://localhost:8080/admin/dashboard](http://localhost:8080/admin/dashboard).
  - username: developer
  - password: developer

You can manage the SSO here:

- [http://localhost:8081/admin/master/console](http://localhost:8081/admin/master/console)
  - username: admin
  - password: admin
