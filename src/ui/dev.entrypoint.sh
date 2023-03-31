#!/bin/sh

export API_ENDPOINT_URL OPENID_ISSUER OPENID_CLIENTID OPENID_REALM

declare -a arr=("/home/app/src/main.ts" "/home/app/src/store/index.ts")

for file in "${arr[@]}";
do
  export file
  if [ ! -f $file.tmpl ]; then
    cp $file $file.tmpl
  fi
  envsubst '$API_ENDPOINT_URL $OPENID_ISSUER $OPENID_CLIENTID $OPENID_REALM' < $file.tmpl > $file

done
echo "Starting website"
npm run serve