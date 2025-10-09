#!/bin/bash

source "$SNAP/configuration/main.sh"

export PATH="$SNAP/bin:$SNAP/usr/sbin:$PATH"

celery -A app.finalized.celery_app worker -n worker2 -Q backup_tasks --concurrency=2 --loglevel=info
