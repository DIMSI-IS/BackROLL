#!/bin/bash

complete -W "dev prod-source prod-hub" backroll-setup
backroll-setup() {
    local backroll_mode=$1
    case $backroll_mode in
        dev)
            ;;
        prod-source|prod-hub)
            local provided_db="Use the MariaDB provided by BackROLL."
            local existing_db="Use your existing MariaDB."
            select choice in "$provided_db" "$existing_db"; do
                case $choice in
                    $provided_db)
                        echo "prov"
                        break
                        ;;
                    $existing_db)
                        echo "exis"
                        break
                        ;;
                esac
            done

            local provided_sso="Use the Keycloak provided by BackROLL."
            local existing_sso="Use your existing Keycloak."
            select choice in "$provided_sso" "$existing_sso"; do
                case $choice in
                    $provided_sso)
                        echo "prov"
                        break
                        ;;
                    $existing_sso)
                        echo "exis"
                        break
                        ;;
                esac
            done
            ;;
        *)
            echo "Invalid backroll_mode argument: expected dev|prod-source|prod-hub"
            return 1
            ;;
    esac

    cp backroll-compose.template.env backroll-compose.env
    sed -i 's/_backroll_mode/'"$backroll_mode"'/' backroll-compose.env

    
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
