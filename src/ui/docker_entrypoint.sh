SRC=/usr/local/apache2/htdocs/config.js

# quoting is required to keep line breaks
NEW_CONFIG="$(./create_config_js.sh $SRC)"
echo "$NEW_CONFIG" > $SRC

# start webserver, e.g. apache or nginx
apachectl -D FOREGROUND;