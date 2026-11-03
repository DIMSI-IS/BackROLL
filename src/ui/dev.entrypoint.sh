#!/bin/sh

echo "Loading environment variables"
for name in BACKROLL_VERSION \
            ;
do
  export VUE_APP_$name=${!name}
done

echo "Starting from sources"
npm run serve
