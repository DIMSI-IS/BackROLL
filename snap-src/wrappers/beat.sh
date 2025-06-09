#!/bin/bash

source "$SNAP/configuration/main.sh"

"$SNAP/bin/celery" -A app.finalized.celery_app beat -S redbeat.RedBeatScheduler --loglevel=info
