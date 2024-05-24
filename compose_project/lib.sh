#!/bin/bash

complete -W "dev prod-source prod-hub" backroll-setup
backroll-setup() {
    cp backroll-compose.template.env backroll-compose.env
    sed -i 's/BACKROLL_MODE=$/BACKROLL_MODE='"$1"'/' backroll-compose.env
    case $1 in
        dev)
            
            ;;
        prod-source)
            
            ;;
        prod-hub)
            
            ;;
    esac
}

backroll-compose() {
    source backroll-compose.env
    export BACKROLL_MODE=$BACKROLL_MODE
    # Write “--profile” for each profile for a better error message when “$@” is empty.
    case $BACKROLL_MODE in
        dev)
            docker compose \
                -f compose.yaml \
                -f compose.source.yaml \
                -f compose.dev.yaml \
                --profile database \
                --profile sso \
                $@
            ;;
        prod-source)
            docker compose \
                -f compose.yaml \
                -f compose.source.yaml \
                -f compose.prod-source.yaml \
                ${BACKROLL_DATABASE:+ --profile database} \
                ${BACKROLL_SSO:+ --profile sso} \
                $@
            ;;
        prod-hub)
            docker compose \
               -f compose.yaml \
               -f compose.prod-hub.yaml \
               $@
            ;;
        *)
            echo "Invalid backroll-compose.env: expected BACKROLL_MODE=dev|prod-source|prod-hub"
            return 1
    esac
}
