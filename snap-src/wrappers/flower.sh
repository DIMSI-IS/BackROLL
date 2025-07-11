#!/bin/bash

source "$SNAP/configuration/main.sh"

"$SNAP/bin/celery" -A app.finalized.celery_app flower --conf=flowerconfig.py --loglevel=info
