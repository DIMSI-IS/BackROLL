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
    case $BACKROLL_MODE in
        dev)
            docker compose -f compose.yaml -f compose.source.yaml -f compose.dev.yaml $@
            ;;
        prod-source)
            docker compose -f compose.yaml -f compose.source.yaml -f compose.prod-source.yaml $@
            ;;
        prod-hub)
            docker compose -f compose.yaml -f compose.prod-hub.yaml $@
            ;;
        *)
            echo "Invalid backroll-compose.env: expected BACKROLL_MODE=dev|prod-source|prod-hub"
            return 1
    esac
}
