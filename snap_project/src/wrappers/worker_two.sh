#!/bin/bash

source "$SNAP/configuration/main.sh"

"$SNAP/bin/celery" -A app.finalized.celery_app worker -n worker2 -Q backup_tasks --concurrency=2 --loglevel=info
