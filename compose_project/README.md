# For the developpers

The development setup is available as two version:

- `dev` with no configuration, network independent
- `staging` with a full configuration process, network dependent

## Quick setup

The `|` means “or”.

```bash
cd compose_project
source source-me.sh dev|staging
docker compose $dev|$staging up
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
- use `docker compose` with argument variables:
  - dev version:
    ```bash
    docker compose $dev …
    ```
  - staging version:
    ```bash
    docker compose $staging …
    ```

Remember to always be in the `compose_project/` directory and to source `source-me.sh` in your terminal.

## Details & UI

Read details about the [dev](./dev.md) version and how to access UI.

Acces to the [staging](./staging.md) UI.
