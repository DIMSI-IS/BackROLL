# Development setup

This docker compose project provides a development version of backroll. The only component that is not included is the KVM host. The project is already set up with a sample configuration.

## Startup

You need to start the docker compose project:
1. Be shure you are in the right directory: `cd backroll-dev`
2. Start the project with docker compose by specifing your local ip address: `HOST_IP=your.local.ip.address docker compose up`

The local ip address is required to make the SSO work.

## User interface

You can access BackROLL at the following address:
- [http://localhost:8080/admin/dashboard](http://localhost:8080/admin/dashboard).
  - username: developer
  - password: developer

You can manage the SSO here:
- [http://localhost:8081/admin/master/console](http://localhost:8081/admin/master/console)
  - username: admin
  - password: admin
