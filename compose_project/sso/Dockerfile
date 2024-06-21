FROM quay.io/keycloak/keycloak:20.0.0

# Fixes logout "invalid parameter: redirect_uri" error but the user name doesn’t show up in the backroll navigation bar.
#FROM quay.io/keycloak/keycloak:17.0

ARG BACKROLL_MODE
COPY @${BACKROLL_MODE}.realm.json /tmp/
RUN /opt/keycloak/bin/kc.sh import --file /tmp/@${BACKROLL_MODE}.realm.json

CMD [ "start-dev" ]
