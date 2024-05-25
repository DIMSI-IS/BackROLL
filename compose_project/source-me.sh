#!/bin/bash

complete -W "dev prod-source prod-hub" backroll-setup
backroll-setup() {
    local backroll_mode=$1
    case $backroll_mode in
        dev)
            sed 's/_backroll_mode/dev/' backroll-compose.template.env > backroll-compose.env
            cp sso/realm.dev.json sso/realm.json
            ;;
        prod-source|prod-hub)
            # Unset variables.
            local use_provided_db=
            local use_provided_sso=

            local provided_db="Use the MariaDB provided by BackROLL."
            local existing_db="Use your existing MariaDB."
            select choice in "$provided_db" "$existing_db"; do
                case $choice in
                    $provided_db)
                        use_provided_db=defined
                        # TODO
                        break
                        ;;
                    $existing_db)
                        # TODO
                        break
                        ;;
                esac
            done

            local provided_sso="Use the Keycloak provided by BackROLL."
            local existing_sso="Use your existing Keycloak."
            select choice in "$provided_sso" "$existing_sso"; do
                case $choice in
                    $provided_sso)
                        use_provided_sso=defined
                        # TODO
                        break
                        ;;
                    $existing_sso)
                        # TODO
                        break
                        ;;
                esac
            done

            for path_name in backroll-compose core database front; do
                local dest=$path_name.env
                cp $path_name.template.env $dest

                for var_name in backroll_mode use_provided_db use_provided_sso; do
                    sed -i 's/_'$var_name'/'${!var_name}'/' $dest
                done
            done
            ;;
        *)
            echo "Invalid backroll_mode argument: expected dev|prod-source|prod-hub"
            return 1
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
            echo docker compose \
                -f compose.yaml \
                -f compose.env.yaml \
                -f compose.source.yaml \
                -f compose.prod-source.yaml \
                ${USE_PROVIDED_DB:+ --profile database} \
                ${USE_PROVIDED_SSO:+ --profile sso} \
                $@
            ;;
        prod-hub)
            docker compose \
               -f compose.yaml \
               -f compose.env.yaml \
               -f compose.prod-hub.yaml \
               $@
            ;;
        *)
            echo "Invalid backroll-compose.env: expected BACKROLL_MODE=dev|prod-source|prod-hub"
            return 1
    esac
}
