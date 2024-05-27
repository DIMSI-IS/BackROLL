echo "Starting BackROLL configuration…"

user="${USERNAME:-${USER:-someone}}"
echo "Current user: $user"

host_directory=compose_project
for key_type in rsa ed25519; do
  key_file="$host_directory/ssh/id_$key_type"
  if ! test -f "$key_file"; then
      echo "Generating $key_type ssh key…"
      ssh-keygen -t $key_type -b 2048 -N "" -C "BackROLL set up by $user" -f "$key_file" -q
      echo "…done."
  fi
done

echo "BackROLL configuration is done."
