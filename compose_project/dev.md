# Development

Development version of BackROLL:

- you must have a KVM host
- no configuration (default values)
- you can go from a local network to another without any trouble

## About starting BackROLL

### First time

The first start is longer than the next ones due to image building and containers’ initialisation. Then the `up` command will continue to run to show you the logs.

The service `setup` will generate ssh keys.

For the moment, the `api` container crashes at the first start because the `database` service is not ready yet. As a quick fix, an automatic restart is set up in the [compose.yaml](./compose.yaml#L38):

```yaml
restart: on-failure
```

In the future, this may be better fixed with a database [healthcheck](https://docs.docker.com/compose/compose-file/05-services/#healthcheck).

### Next times

Use the `docker compose start` command:

```bash
docker compose $dev start
```

To re-generate the ssh keys, delete them from [ssh/](./ssh/) before starting.

#### Note

For the moment, only the RSA key is shown in the UI but you can also use the Ed25519 key.

## Building BackROLL again

If you have changed the source code of one of the containers, you may have to build it and start it again. Example:

```bash
docker compose $dev build sso
docker compose $dev create sso
docker compose $dev start sso
```

Some of the container have their sources mounted. Check out [compose.sources.yaml](./compose.source.yaml). In this case, just restart the container. Example:

```bash
docker compose $dev restart api
```

## User interface

### Proxy setup

To access the various containers’ web interfaces, your internet browser needs to get into the compose project network.

#### Running the proxy server

Create a proxy server by connecting to the proxy container:

```bash
ssh -p 2222 -D 1080 developer@localhost
```

The password is `developer`. You must ensure that the command is running each time you start working on BackROLL.

If you are working on a shared developement server, the port 2222 may be already in use. Run the `docker port` command on the proxy container to find the exposed port.

#### Connecting to the proxy server

Now you need to configure your web browser to use the SOCKS v5 proxy at address `localhost` port `1080` and to use the proxy’s DNS. Feel free to use another port if it is more convenient for you.

For Firefox, see [Connection settings in Firefox](https://support.mozilla.org/en-US/kb/connection-settings-firefox):

- choose “Manual proxy configuration”
- fill in “SOCKS Host” and “Port”
- choose “SOCKS v5”
- check “Proxy DNS when using SOCKS v5”

#### Note

Thanks to the proxy server, only one port of the host is used and the SSO always have the same address. This is useful if you work remotely or if you are not always working on the same network.

Mind that both your web browser and the `api` container must access to the SSO with the same URL.

### BackROLL

You can access BackROLL at the following address:

- [http://front:8080/admin/dashboard](http://front:8080/admin/dashboard).
  - username: developer
  - password: developer

#### Storage path

On the “Storage” page, when you click on the “Add new storage” button, you are asked to give a path. For this development setup, use `/mnt/docker_storage/`. A Docker volume is mounted at this point.

#### Note

Clicking on "Dashboard" may crash the whole menu. You need to reload the page to make it work again. It occurs if the "used" value of a storage can not be read.

### Keycloak

You can manage the [Keycloak](https://www.keycloak.org/) SSO here:

- [http://sso:8080/admin/master/console/#/backroll](http://sso:8080/admin/master/console/#/backroll)
  - username: admin
  - password: admin

### Flower

You can monitor the [Celery](https://docs.celeryq.dev/en/stable/) tasks on the [Flower](https://flower.readthedocs.io/en/latest/) interface:

- [http://flower:5555/](http://flower:5555/)
