#!/bin/bash

source "$SNAP/configuration/main.sh"

export PATH="$SNAP/bin:$SNAP/usr/sbin:$PATH"

uvicorn app.finalized:starlette_app --host 0.0.0.0 --port 5050
