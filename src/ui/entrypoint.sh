source_path="$1"
destination_path="$2"

cp -r "$source_path"/* "$destination_path"/
for path in "$destination_path"/js/*; do
    # TODO envsubst everything ie do not list variables ?
    envsubst '$BACKROLL_VERSION' < "$path" > envsubst_output
    mv envsubst_output "$path"
done

nginx -g 'daemon off;'
