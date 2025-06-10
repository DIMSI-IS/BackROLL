#!/bin/bash

source "$SNAP/configuration/main.sh"

# cd "$SNAP/lib/node_modules/app"
# export PATH="$PATH"

# "$SNAP/bin/npm" run serve
# => vue-cli-service not found

src="$SNAP/ui"
dst="$SNAP_DATA/usr/share/nginx/html"

echo "----"
ls "$src"
echo "----"

# TODO Fix entrypoint.sh an call it if production with Docker is still relevant.
# Use layout to make nginx call work ?

cp -r "$src"/* "$dst"/
for path in "$dst"/js/*; do
    envsubst '$BACKROLL_VERSION $API_ENDPOINT_URL $OPENID_ISSUER $OPENID_CLIENTID $OPENID_REALM' < "$path" > envsubst_output
    mv envsubst_output "$path"
done

echo "----"
ls "$dst"
echo "----"

"$SNAP/usr/sbin/nginx" -g "daemon off;"
