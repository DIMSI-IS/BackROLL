#!/bin/bash

source "$SNAP/configuration/main.sh"

export PATH="$SNAP/bin:$SNAP/usr/sbin:$PATH"

celery -A app.finalized.celery_app flower --conf=flowerconfig.py --loglevel=info
