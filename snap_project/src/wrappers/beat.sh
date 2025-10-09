#!/bin/bash

source "$SNAP/configuration/main.sh"

export PATH="$SNAP/bin:$SNAP/usr/sbin:$PATH"

celery -A app.finalized.celery_app beat -S redbeat.RedBeatScheduler --loglevel=info
