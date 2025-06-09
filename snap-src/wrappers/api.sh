#!/bin/bash

source "$SNAP/configuration/main.sh"

"$SNAP/bin/uvicorn" app.finalized:starlette_app --host 0.0.0.0 --port 5050
