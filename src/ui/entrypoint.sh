#!/bin/sh

echo "Replacing environment variables"
for file in /usr/share/nginx/html/js/*; do
  mv "$file" "$file.tmp"
  envsubst '$BACKROLL_VERSION $API_ENDPOINT_URL $OPENID_ISSUER $OPENID_CLIENT_UI_ID $OPENID_REALM $DEFAULT_USER_NAME' < "$file.tmp" > "$file"
  rm "$file.tmp"
done

echo "Starting from build"
nginx -g 'daemon off;'
