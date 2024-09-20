#!/bin/sh

echo "Loading environment variables"
for name in BACKROLL_VERSION \
            API_ENDPOINT_URL \
            OPENID_ISSUER \
            OPENID_REALM \
            OPENID_CLIENTID \
            ;
do
  export VUE_APP_$name=${!name}
done

echo "Starting from sources"
npm run serve
