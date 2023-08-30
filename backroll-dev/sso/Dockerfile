#FROM quay.io/keycloak/keycloak:22.0.1

# Fixes logout "invalid parameter: redirect_uri" error but the user name doesn’t show up in the backroll navigation bar.
FROM quay.io/keycloak/keycloak:17.0

COPY realm.json /tmp/
RUN /opt/keycloak/bin/kc.sh import --file /tmp/realm.json

CMD [ "start-dev" ]
