#!/bin/bash

source "$SNAP/configuration/main.sh"

"$SNAP/bin/celery" -A app.finalized.celery_app worker -n worker -Q default --concurrency=4 --loglevel=info
