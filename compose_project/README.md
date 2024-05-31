# For the developpers

The development setup is available as two version:
- `dev` with no configuration, network independent
- `staging` with a full configuration process, network dependent

## Quick intallation process

The `|` means “or”.

```bash
cd compose_project
source source-me.sh
backroll-setup dev|staging
backroll-compose up
```

## Details: the helper script

In the [compose_project/](.) directory, the script [source-me.sh](./source-me.sh) provides helpers for configuring and running BackROLL:

- ensure that you are in the [compose_project/](.) directory:
```bash
cd compose_project
```

- source the script [source-me.sh](./source-me.sh):
```bash
source source-me.sh
```

- setup one version:

```bash
backroll-setup dev
```
or
```bash
backroll-setup staging
```

- use `backroll-compose` instead of `docker compose`: it adds arguments to the command depending on you configuration. Just use it as the `docker compose` command:

```
backroll-compose build
backroll-compose create
backroll-compose start
…
```

Remember to always be in the `compose_project/` directory and to source `source-me.sh` in your terminal.

## Versions

Details:
- first read about [dev](./dev.md)
- [staging](./staging.md)
