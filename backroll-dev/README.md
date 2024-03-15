# Development setup

This docker compose project provides a development version of backroll. The only component that is not included is the KVM host. This is intented for localhost development only so that the configuration is already done with default values.

## Starting BackROLL

### First time

```sh
cd backroll-dev
docker compose up
```

An automatic setup will generate an ssh key.

The first start is longer than the next ones due to image building and containers’ initialisation. Then the up command will continue to run to show you the logs.

#### Note

For the moment, the api container crashes at the first start because the database is not ready yet. As a quick fix, an automatic restart is set up in the [docker-compose.yml](./docker-compose.yml):

```yaml
restart: on-failure
```

In the future, this may be better fixed with a database [healthcheck](https://docs.docker.com/compose/compose-file/05-services/#healthcheck).

### Next times

This time, use the start command:

```sh
cd backroll-dev
docker compose start
```

or else you can use the Docker Desktop UI, the Docker extension for Visual Studio Code or any other Docker UI.

To re-generate the ssh key, delete `backroll-dev/ssh/id` before starting.

## Building BackROLL again

If you have changed the source code of one of the containers, you may have to build it and start it again. Example:

```sh
cd backroll-dev
docker compose build sso
docker compose create sso
docker compose start sso
```

## User interface

### Proxy setup

To access the various containers’ web interfaces, you internet browser needs to get into the compose project network.

#### Running the proxy server

Create a proxy server by connecting to the proxy container:

```sh
ssh -p 2222 -D 1080 developer@localhost
```

The password is `developer`. You must ensure that the command is running each time you start working on BackROLL.

#### Connecting to the proxy server

Now you need to configure your web browser to use the SOCKS v5 proxy at address `localhost` port `1080` and to use the proxy’s DNS. Feel free to use another port if it is more convenient for you.

For Firefox, see [Connection settings in Firefox](https://support.mozilla.org/en-US/kb/connection-settings-firefox):
- choose “Manual proxy configuration”
- fill in “SOCKS Host” and “Port”
- choose “SOCKS v5”
- check “Proxy DNS when using SOCKS v5”

#### Note

The proxy server helps reducing the configuration to do to run the project. Otherwise you would have to configure a local network IP address for the SSO, or a docker network IP address (this trick only works for Windows). Mind that both your web browser and the api container must access to the SSO with the same URL.

### BackROLL

You can access BackROLL at the following address:

- [http://front:8080/admin/dashboard](http://front:8080/admin/dashboard).
  - username: developer
  - password: developer

#### Storage path

On the “Storage” page, when you click on the “Add new storage” button, you are asked to give a path. For this development setup, use `/mnt/storage/`. A Docker volume is mounted at this point.

#### Note

Clicking on "Dashboard" may crash the whole menu. You need to reload the page to make it work again. It occurs if the "used" value of a storage can not be read.

### Keycloak

You can manage the [Keycloak](https://www.keycloak.org/) SSO here:

- [http://sso:8080/admin/master/console/#/backroll](http://sso:8080/admin/master/console/#/backroll)
  - username: admin
  - password: admin

Include the changes you want to keep for every BackROLL developer in [backroll-dev/sso/realm.json](./sso/realm.json).

### Flower

You can monitor the [Celery](https://docs.celeryq.dev/en/stable/) tasks on the [Flower](https://flower.readthedocs.io/en/latest/) interface:
- [http://flower:5555/](http://flower:5555/)
