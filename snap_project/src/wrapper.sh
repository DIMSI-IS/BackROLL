#!/bin/bash

service="$1"

source "$SNAP/configuration/main.sh"
export PATH="$SNAP/bin:$SNAP/usr/sbin:$PATH"

case "$service" in
    flower)
        cp "$SNAP/flower_config.py" ./
        ;;
esac

bash "$SNAP/commands/$service.sh"
