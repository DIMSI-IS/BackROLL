#!/bin/bash

source "$SNAP/configuration/main.sh"

export PATH="$SNAP/bin:$SNAP/usr/sbin:$PATH"

celery -A app.finalized.celery_app worker -n worker -Q default --concurrency=4 --loglevel=info
