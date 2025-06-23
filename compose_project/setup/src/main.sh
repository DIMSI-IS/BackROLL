echo "Starting BackROLL configuration by $BACKROLL_HOST_USER…"

host_directory=compose_project

# Note that here, it is too late to set variables in environnement files.
# The values defined now will be read only at the next start.

# SSH directory
ssh_directory="$host_directory/core/ssh/@$BACKROLL_MODE"
mkdir -p "$ssh_directory"

echo "BackROLL configuration is done."
