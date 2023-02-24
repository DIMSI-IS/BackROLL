#!/bin/sh

source ../../common/config/ui/env

for file in /usr/share/nginx/html/js/*;
do
  if [ ! -f $file.tmpl ]; then
    cp $file $file.tmpl
  fi
  envsubst '$BACKROLL_API_ENDPOINT_URL $BACKROLL_OPENID_ISSUER_URL $BACKROLL_OPENID_CLIENTID $BACKROLL_OPENID_REALM' < $file.tmpl > $file

done
echo "Starting Nginx"
nginx -g 'daemon off;'