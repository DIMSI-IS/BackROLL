#!/bin/bash

command_name="$1"

source "$SNAP/configuration/main.sh"
export PATH="$SNAP/bin:$SNAP/usr/sbin:$PATH"

bash "$SNAP/commands/$command_name.sh"
