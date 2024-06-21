#!/bin/sh

echo "Loading environment variables"
for name in API_ENDPOINT_URL OPENID_ISSUER OPENID_REALM OPENID_CLIENTID; do
  export VUE_APP_$name=${!name}
done

echo "Starting website"
npm run serve
