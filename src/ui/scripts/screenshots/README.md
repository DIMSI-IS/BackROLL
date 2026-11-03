# Documentation screenshots

Regenerates the pictures of the in-app documentation (`public/docs/en/*.png` and
`public/docs/fr/*.png`) from the real UI, with fictional data and no backend.

- `mock_server.py`: FastAPI app that serves the built UI and mocks `/api/v1/...` (fictional machines
  `web-01`, `db-01`..., hypervisors `kvm-01`/`kvm-02`, documentation addresses only).
  Demo login of the mock: `admin` / `demo-admin-pass`.
- `capture.py`: starts the mock on a free port, drives the installed Chrome (or Edge) with Playwright
  (no browser is downloaded), logs in through the login page and saves the pictures.

## Steps

1. Build the UI outside the repository (about 2 minutes), from `src/ui`:

   ```sh
   NODE_OPTIONS=--openssl-legacy-provider npx vue-cli-service build --dest "$TEMP/ui-docs-build"
   ```

2. Install the Python packages (Pillow is optional, it shrinks the PNG files):

   ```sh
   python -m pip install fastapi uvicorn playwright pillow
   ```

   Do not run `playwright install`: Chrome or Edge must already be installed.

3. Take the pictures, from `src/ui/scripts/screenshots`:

   ```sh
   python capture.py --dist "$TEMP/ui-docs-build"
   ```

   Options: `--only dashboard,policies` (some pictures), `--langs en` (one language).
   A picture that fails is reported at the end, with a screenshot of the page in the temporary folder.

Pictures: dashboard, topbar, policies, policy-form, pools, hypervisors, virtual-machines,
virtual-machine, backup-files, tasks-backup, kickstart, drp (taller window, 1440x1300, to show the form
and the history), users, audit-log, settings, connectors, storage, external-hooks.
