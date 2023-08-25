FROM quay.io/keycloak/keycloak:22.0.1

COPY realm.json /tmp/
RUN /opt/keycloak/bin/kc.sh import --file /tmp/realm.json

CMD [ "start-dev" ]
