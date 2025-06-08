#!bin/bash

bash "$SNAP/configure/main.sh"

# TODO test if the bin/ is mandatory.
uvicorn

bin/uvicorn app.finalized:starlette_app --host 0.0.0.0 --port 5050
