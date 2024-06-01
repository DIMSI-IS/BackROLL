#!/bin/bash

backroll-setup() {
    local backroll_mode=$1
    case $backroll_mode in
        prod)
            echo "Not yet implemented." 1>&2
            return 1
            ;;
        dev|staging|prod)
            # Unset variables.
            local use_provided_db=
            local use_provided_sso=

            case $backroll_mode in
                dev)
                    flower_user=
                    flower_password=
                    db_root_password=root
                    db_address=database
                    db_port=3306
                    db_name=backroll
                    db_user_name=backroll
                    db_user_password=backroll
                    sso_admin_name=admin
                    sso_admin_password=admin
                    sso_address=sso
                    sso_client_secret=e7cbb6ae88ce7cd7cf3b104a972d08ed
                    sso_user_name=developer
                    sso_user_password=developer
                    api_address=api
                    front_address=front
                    ;;
                staging|prod)
                    local host_ip=$(hostname -I | awk '{print $1}') # TODO Or use hostname ?
                    api_address=$host_ip
                    front_address=$host_ip

                    echo "#### Flower configuration (preview) ####"
                    read -r -p "Define new flower username : " flower_user
                    while true;
                    do 
                        read -s -p "Define new flower password : " flower_password
                        echo
                        read -s -p "Confirm password : " confirmed_password
                        echo

                        [[ "$flower_password" == "$confirmed_password" ]] && break

                        echo "Passwords do not match. Try again."
                    done

                    echo "#### Database configuration ####"
                    local provided_db="Use the MariaDB database provided by BackROLL."
                    local existing_db="Use your existing MariaDB database. (preview)"
                    select choice in "$provided_db" "$existing_db"; do
                        case $choice in
                            "$provided_db"|"$existing_db")
                                [[ "$choice" == "$provided_db" ]] && use_provided_db=defined

                                local action=
                                case $choice in
                                    "$provided_db")
                                        action="Define new"

                                        db_address=database
                                        db_port=3306
                                        while true;
                                        do 
                                            read -s -p "$action MariaDB database root password : " db_root_password
                                            echo
                                            read -s -p "Confirm password : " confirmed_password
                                            echo

                                            [[ "$db_root_password" == "$confirmed_password" ]] && break

                                            echo "Passwords do not match. Try again."
                                        done
                                        ;;
                                    "$existing_db")
                                        action="Enter existing"

                                        read -r -p "$action MariaDB database address : " db_address
                                        read -r -p "$action MariaDB database port : " db_port
                                        ;;
                                esac
                                read -r -p "$action MariaDB database name : " db_name
                                read -r -p "$action MariaDB database username : " db_user_name
                                while true;
                                do 
                                    read -s -p "$action MariaDB database password : " db_user_password
                                    echo
                                    read -s -p "Confirm password : " confirmed_password
                                    echo

                                    [[ "$db_user_password" == "$confirmed_password" ]] && break

                                    echo "Passwords do not match. Try again."
                                done

                                break
                                ;;
                        esac
                    done

                    echo "#### SSO configuration ####"
                    local provided_sso="Use the Keycloak provided by BackROLL."
                    local existing_sso="Use your existing Keycloak. (preview)"
                    select choice in "$provided_sso" "$existing_sso"; do
                        case $choice in
                            "$provided_sso"|"$existing_sso")
                                [[ "$choice" == "$provided_sso" ]] && use_provided_sso=defined
                                break
                                ;;
                        esac
                    done

                    sso_client_secret=$(date | md5sum)
                    sso_client_secret=(${sso_client_secret// / })
                    sso_client_secret=${sso_client_secret[0]}

                    echo "#### Keycloak first user configuration ####"
                    read -r -p "Define new Keycloak username : " sso_user_name
                    while true;
                    do 
                        read -s -p "Define new Keycloak password : " sso_user_password
                        echo
                        read -s -p "Confirm password : " confirmed_password
                        echo

                        [[ "$sso_user_password" == "$confirmed_password" ]] && break

                        echo "Passwords do not match. Try again."
                    done

                    local sso_address="http://$host_ip:8081"
                    if [[ "$use_provided_sso" == "" ]]; then
                        echo "#### Existing Keycloak configuration ####"
                        read -r -p "Enter existing Keyclock url (ex : http://localhost:8080) : " sso_address
                    else
                        echo "#### New Keycloak configuration ####"
                        read -r -p "Define new Keyclock admin name : " sso_admin_name
                        while true;
                            do 
                                read -s -p "Define new Keycloak admin password : " sso_admin_password
                                echo
                                read -s -p "Confirm password : " confirmed_password
                                echo

                                [[ "$sso_admin_password" == "$confirmed_password" ]] && break

                                echo "Passwords do not match. Try again."
                            done
                    fi
                    ;;
            esac

            for template_path in $(find . -wholename "*/template.*" 2>/dev/null); do
                path="${template_path/template./@$backroll_mode.}"

                cp "$template_path" "$path"

                for var_name in backroll_mode \
                                flower_user \
                                flower_password \
                                use_provided_db \
                                use_provided_sso \
                                db_root_password \
                                db_address \
                                db_port \
                                db_name \
                                db_user_name \
                                db_user_password \
                                sso_admin_name \
                                sso_admin_password \
                                sso_address \
                                sso_client_secret \
                                sso_user_name \
                                sso_user_password \
                                api_address \
                                front_address \
                                ;
                do
                    sed -i 's|_'"$var_name"'|'"${!var_name}"'|' "$path"
                done
            done

            if [[ "$backroll_mode" != dev ]] && [[ "$use_provided_sso" == "" ]]; then
                read -r -p "Enter existing Keyclock realm (master): " keycloak_realm
                keycloak_realm="${keycloak_realm:=master}"
                read -r -p "Enter existing Keyclock admin client_id (admin-cli) : " admin_client_id
                admin_client_id="${admin_client_id:=admin-cli}"
                read -s -p "Enter existing Keyclock admin client_secret : " admin_client_secret
                echo
                token=$(curl -s -X POST "$sso_address/realms/$keycloak_realm/protocol/openid-connect/token" \
                    -H "Content-Type: application/x-www-form-urlencoded" \
                    -d "grant_type=client_credentials&client_id=$admin_client_id&client_secret=$admin_client_secret" \
                    | grep -oP '"access_token":"\K[^"]+')

                curl -X POST "$sso_address/admin/realms" \
                    -H "Content-Type: application/json" \
                    -H "Authorization: Bearer $token" \
                    -d "$(cat sso/realm.json)"
            fi
            ;;
        *)
            echo "Usage: backroll-setup <dev|staging|prod>" 1>&2
            return 1
            ;;
    esac
}

if [[ "$1" != "" ]]; then
    backroll-setup "$1"
fi

if source backroll-compose/@dev.env 2>/dev/null; then
    dev="--env-file backroll-compose/@dev.env -f compose.yaml -f compose.source.yaml -f compose.dev.yaml --profile database --profile sso"
fi

if source backroll-compose/@staging.env 2>/dev/null; then
    staging="--env-file backroll-compose/@staging.env -f compose.yaml -f compose.source.yaml -f compose.staging_prod.yaml ${USE_PROVIDED_DB:+ --profile database} ${USE_PROVIDED_SSO:+ --profile sso}"
fi

echo "
Docker compose argument variables:
  - dev=${dev:-    # Run “source source-me.sh dev” to setup dev.}
  - staging=${staging:-    # Run “source source-me.sh staging” to setup staging.}

Usage:
  - docker compose \$dev …
  - docker compose \$staging …
"
