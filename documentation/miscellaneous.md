# Miscellaneous

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

## About the `dev` proxy server

Thanks to the proxy server, only one port of the host is used and the SSO always have the same address. This is useful if you work remotely or if you are not always working on the same network.

Mind that both your web browser and the `api` container must access to the SSO with the same URL.

## User interface

### The `dev` storage path

On the “Storage” page, when you click on the “Add new storage” button, you are asked to give a path. For this development setup, use `/mnt/docker_storage/`. A Docker volume is mounted at this point.
