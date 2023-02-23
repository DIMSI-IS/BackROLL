#!/bin/sh
for file in /usr/share/nginx/html/js/*;
do
  if [ ! -f $file.tmpl ]; then
    cp $file $file.tmpl
  fi
  envsubst 'http://localhost:5050 https://sso.dimsi.io/auth backroll master' < $file.tmpl > $file

done
echo "Starting Nginx"
nginx -g 'daemon off;'