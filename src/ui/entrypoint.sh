source_path="$1"
destination_path="$2"

echo src="$source_path"
echo dst="$destination_path"

cp -r "$source_path"/* "$destination_path"/
for path in "$destination_path"/js/*; do
    envsubst '$BACKROLL_VERSION $OPENID_ISSUER $OPENID_REALM $OPENID_CLIENT_UI_ID $DEFAULT_USER_NAME' < "$path" > envsubst_output
    mv envsubst_output "$path"
done

nginx -g 'daemon off;'
