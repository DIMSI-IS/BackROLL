# Intented to be run with the bash source command.

export BACKROLL_HOSTNAME=$HOSTNAME
export BACKROLL_HOST_USER=$(echo "${USERNAME:-${USER:-someone}}" | sed 's/\./-/g')
