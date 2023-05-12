#!/bin/sh

for file in /usr/share/nginx/html/js/*;
do
  if [ ! -f $file.tmpl ]; then
    cp $file $file.tmpl
  fi
  envsubst '$API_ENDPOINT_URL $OPENID_ISSUER $OPENID_CLIENTID $OPENID_REALM' < $file.tmpl > $file
  
done

echo "Starting Nginx"
nginx -g 'daemon off;'