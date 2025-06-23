echo "Starting BackROLL configuration by $BACKROLL_HOST_USER…"

host_directory=compose_project

# Note that here, it is too late to set variables in environnement files.
# The values defined now will be read only at the next start.

# SSH directory
ssh_directory="$host_directory/core/ssh/@$BACKROLL_MODE"
mkdir -p "$ssh_directory"

# SSH config
cp "$host_directory/core/ssh/config" "$ssh_directory/"

# SSH keys
for key_type in rsa ed25519; do
  key_file="$ssh_directory/id_$key_type"
  if ! test -f "$key_file"; then
      echo "Generating $key_type ssh key…"
      ssh-keygen -t $key_type -b 2048 -N "" -C "$BACKROLL_HOST_USER@$BACKROLL_HOSTNAME(backroll)" -f "$key_file" -q
      echo "…done."
  fi
done

echo "BackROLL configuration is done."
