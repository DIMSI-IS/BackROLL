echo "Starting BackROLL configuration…"

key_file=ssh/id_rsa
if ! test -f "$key_file"; then
    echo "Generating ssh key…"
    ssh-keygen -b 2048 -t rsa -f "$key_file" -q -N ""
    echo "…done."
fi

echo "BackROLL configuration is done."