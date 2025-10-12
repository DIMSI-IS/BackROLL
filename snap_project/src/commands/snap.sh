#!/bin/bash

service="$1"
shift 1
arguments="$@"

source "$SNAP/app/configuration/main.sh"
export PATH="$SNAP/bin:$SNAP/usr/sbin:$PATH"

case "$service" in
    flower)
        cp "$SNAP/app/flower_config.py" ./
        ;;
esac

bash "$SNAP/app/commands/$service.sh" $@
