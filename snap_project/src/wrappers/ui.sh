#!/bin/bash

source "$SNAP/configuration/main.sh"

# cd "$SNAP/lib/node_modules/app"
# export PATH="$PATH"

# "$SNAP/bin/npm" run serve
# => vue-cli-service not found

src="$SNAP/ui"
dst="$SNAP_DATA/usr/share/nginx/html"

# TODO Update entrypoint.sh an call it if production with Docker is still relevant.
# Use layout to make nginx call work ?

cp -r "$src"/* "$dst"/
for path in "$dst"/js/*; do
    envsubst '$BACKROLL_VERSION $OPENID_ISSUER $OPENID_REALM $OPENID_CLIENT_UI_ID $DEFAULT_USER_NAME' < "$path" > envsubst_output
    mv envsubst_output "$path"
done

export PATH="$SNAP/bin:$SNAP/usr/sbin:$PATH"

nginx -g "daemon off;"
