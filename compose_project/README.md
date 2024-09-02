# For the developpers

The development setup is available as two version:

- `dev`:
  - no configuration (default values)
  - you can go from a local network to another without any trouble
- `staging`:
  - you will follow the configuration steps
  - it depends on your local network

## Quick setup

### `dev`

```bash
cd compose_project
source source-me.sh dev
docker compose $dev up
```

### `staging`

```bash
cd compose_project
source source-me.sh staging
docker compose $staging up
```

### `prod`

```bash
cd compose_project
source source-me.sh prod
docker compose $prod up
```

### Details: the helper script

In the [compose_project/](.) directory, the script [source-me.sh](./source-me.sh) helps you to configure and run BackROLL:

- ensure that you are in the [compose_project/](.) directory:

  ```bash
  cd compose_project
  ```

- source the script [source-me.sh](./source-me.sh):
  - only get argument variables:
    ```bash
    source source-me.sh
    ```
  - get argument variables and setup dev:
    ```bash
    source source-me.sh dev
    ```
  - get argument variables and setup staging:
    ```bash
    source souce-me.sh staging
    ```
  - get argument variables and setup prod:
    ```bash
    source souce-me.sh prod
    ```
- use `docker compose` with argument variables:
  - dev version:
    ```bash
    docker compose $dev …
    ```
  - staging version:
    ```bash
    docker compose $staging …
    ```
  - prod version:
    ```bash
    docker compose $prod …
    ```

Remember to always be in the `compose_project/` directory and to source `source-me.sh` in your terminal.

## User interface

The user interface is made up of several components:

- the BackROLL front
- the [Flower](https://flower.readthedocs.io/en/latest/) web application to monitor and manage the [Celery](https://docs.celeryq.dev/en/stable/) tasks.
- the [Keycloak](https://www.keycloak.org/) SSO admin console

### Accessing `dev` UI

#### Proxy setup

To access the various containers’ web interfaces, your internet browser needs to get into the compose project network.

##### Running the proxy server

Create a proxy server by connecting to the proxy container:

```bash
ssh -p 2222 -D 1080 developer@localhost
```

The password is `developer`. You must ensure that the command is running each time you start working on BackROLL.

If you are working on a shared developement server, the port 2222 may be already in use. Run the `docker port` command on the proxy container to find the exposed port.

##### Connecting to the proxy server

Now you need to configure your web browser to use the SOCKS v5 proxy at address `localhost` port `1080` and to use the proxy’s DNS. Feel free to use another port if it is more convenient for you.

For Firefox, see [Connection settings in Firefox](https://support.mozilla.org/en-US/kb/connection-settings-firefox):

- choose “Manual proxy configuration”
- fill in “SOCKS Host” and “Port”
- choose “SOCKS v5”
- check “Proxy DNS when using SOCKS v5”

#### URLs and credentials

BackROLL:

- [http://front:8080/admin/dashboard](http://front:8080/admin/dashboard).
  - username: developer
  - password: developer

Keycloak:

- [http://sso:8080/admin/master/console/#/backroll](http://sso:8080/admin/master/console/#/backroll)
  - username: admin
  - password: admin

Flower:

- [http://flower:5555/](http://flower:5555/)

### Accessing `staging` and `prod` UI

You can acces to the user interfaces on localhost:

- BackROLL [http://localhost:8080/admin/dashboard](http://localhost:8080/admin/dashboard)
- Flower [http://localhost:5555/](http://localhost:5555/)
- Keycloak [http://localhost:8081/admin/master/console/#/backroll](http://localhost:8081/admin/master/console/#/backroll)

## Miscellaneous

Various details about the current state of the project: [miscellaneous.md](./miscellaneous.md).
