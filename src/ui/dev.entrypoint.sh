#!/bin/sh

#export API_ENDPOINT_URL OPENID_ISSUER OPENID_CLIENTID OPENID_REALM

file=".env.local"

export file
if [ ! -f $file.tmpl ]; then
  cp $file $file.tmpl
fi
envsubst '$API_ENDPOINT_URL $OPENID_ISSUER $OPENID_CLIENTID $OPENID_REALM' < $file.tmpl > $file

echo "Starting website"
npm run serve