# Backroll compose projects

The Docker Compose projects enable Backroll to be available in several modes :

- for developpement :
  - `dev`:
    - no configuration (default values)
    - uses the Docker Compose network
  - `staging`:
    - you will go through the configuration steps
    - uses your local network
- for production : `prod`

## The helper script

In the [compose_project/](.) directory, the script [source-me.sh](./source-me.sh) helps you to configure and run Backroll :

- ensure that you are in the `compose_project/` directory :

  ```bash
  cd compose_project
  ```

- source the script `source-me.sh` :
  - only get argument variables :
    ```bash
    source source-me.sh
    ```
  - get argument variables and setup `dev` :
    ```bash
    source source-me.sh setup-dev
    ```
  - get argument variables and setup `staging` :
    ```bash
    source source-me.sh setup-staging
    ```
  - get argument variables and setup `prod` :
    ```bash
    source source-me.sh setup-prod
    ```
- use [`docker compose`](https://docs.docker.com/reference/cli/docker/compose/) with an argument variable :
  - dev version :
    ```bash
    docker compose $dev [options] [COMMAND] [ARGS...]
    ```
  - staging version :
    ```bash
    docker compose $staging [options] [COMMAND] [ARGS...]
    ```
  - prod version :
    ```bash
    docker compose $prod [options] [COMMAND] [ARGS...]
    ```

Remember to always be in the `compose_project/` directory and to source `source-me.sh` in your terminal.

### Examples

#### `dev`

```bash
cd compose_project
source source-me.sh setup-dev
docker compose $dev up
```

#### `staging`

```bash
cd compose_project
source source-me.sh setup-staging
docker compose $staging up
```

#### `prod`

```bash
cd compose_project
source source-me.sh setup-prod
docker compose $prod up
```

## User interface

The user interface is made up of several components :

- the Backroll front
- the [Flower](https://flower.readthedocs.io/en/latest/) web application to monitor and manage the [Celery](https://docs.celeryq.dev/en/stable/) tasks
- the [Keycloak](https://www.keycloak.org/) SSO admin console

### Accessing the `dev` UI

#### Proxy setup

To access the various containers’ web interfaces, your internet browser needs to get into the compose project network.

##### Running the proxy server

Create a proxy server by connecting to the proxy container:

```bash
ssh -p 2222 -D 1080 developer@localhost
```

The password is `developer`. You must ensure that the command is running each time you start working on Backroll.

If you are working remotely, do not forget to forward the port 2222.

> ⚠️ **Warning:** keep in mind that the port 2222 may be already in use. Run the following command to find the exposed port of the proxy container.
```bash 
docker port <proxy_container_name>
```


For example, the diagram below illustrates how your browser traffic flows if you are working remotely (proxy port is 2230 here for example) :
```
Firefox (configured to use SOCKS proxy at localhost:1080)
         │
         │  <-- SOCKS v5 proxy tunnel established by SSH -D 1080
         ▼
Local machine
         │
         │  <-- SSH local port forwarding (2230)
         ▼
Developpement server port 2230
         │
         │  <-- Docker port mapping from host port 2230 to container port 2222
         ▼
Proxy container port 2222 (inside the Developpement server)
```

##### Connecting to the proxy server

Now you need to configure your web browser to use the SOCKS v5 proxy at address `localhost` port `1080` and to use the proxy DNS. Feel free to use another port if it is more convenient for you.

For Firefox, see [Connection settings in Firefox](https://support.mozilla.org/en-US/kb/connection-settings-firefox) :

- choose “Manual proxy configuration”
- fill in “SOCKS Host” and “Port”
- choose “SOCKS v5”
- check “Proxy DNS when using SOCKS v5”

#### URLs and credentials

Backroll :

- URL : http://front:8080/admin/dashboard
- username : developer
- password : developer

Keycloak :

- URL : http://sso:8080/admin/master/console/#/backroll
- username : admin
- password : admin

Flower :

- http://flower:5555/

### Accessing the `staging` or `prod` UI

You can acces to the user interfaces on localhost :

- Backroll :
  - `staging` http://localhost:8080/admin/dashboard
  - `prod` http://localhost/admin/dashboard
- Flower http://localhost:5555/
- Keycloak http://localhost:8081/admin/master/console/#/backroll
