#!/bin/sh

echo "Replacing environment variables"
for file in /usr/share/nginx/html/js/*; do
  mv "$file" "$file.tmp"
  # TODO Only works the first time or else the change are not saved before restarting.
  envsubst '$BACKROLL_VERSION $OPENID_ISSUER $OPENID_CLIENT_UI_ID $OPENID_REALM $DEFAULT_USER_NAME' < "$file.tmp" > "$file"
  rm "$file.tmp"
done

echo "Starting from build"
nginx -g 'daemon off;'
