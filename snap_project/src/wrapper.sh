#!/bin/bash

# TODO Rename command.sh ?

service="$1"
shift 1
arguments="$@"

source "$SNAP/configuration/main.sh"
export PATH="$SNAP/bin:$SNAP/usr/sbin:$PATH"

case "$service" in
    flower)
        cp "$SNAP/flower_config.py" ./
        ;;
esac

bash "$SNAP/commands/$service.sh" $@
