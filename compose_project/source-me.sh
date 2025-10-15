# Intented to be run with the bash source command.

backroll_setup() {
    backroll_mode=$1
    case $backroll_mode in
        dev|staging|prod)
            # Unset variables.
            backroll_db=
            backroll_sso=

            case $backroll_mode in
                dev)
                    backroll_db=defined
                    backroll_sso=defined

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
                    sso_base_url=http://sso:8080
                    sso_client_secret=e7cbb6ae88ce7cd7cf3b104a972d08ed
                    sso_user_name=developer
                    sso_user_password=developer
                    front_url=http://front:8080
                    ;;
                staging|prod)
                    case $backroll_mode in
                        prod)
                            if ! git describe --tags --exact-match 2>/dev/null; then
                                read -r -p "You are not on a release commit. Run version mismatch protection ? " response
                                if [[ "$response" != "I know that prod will fail." ]]; then
                                    echo "Running version mismatch protection…"
                                    git checkout $(git describe --tags --abbrev=0) || return 1
                                fi
                            fi
                            ;;
                    esac

                    echo "#### BackROLL host IP configuration ####"
                    local host_ip_list=$(hostname -I)
                    echo "Select the access IP you want to use :"
                    local host_ip=
                    select choice in Other $host_ip_list; do
                        case $choice in
                            "")
                                ;;
                            Other)
                                read -r -p "Enter existing BackROLL host IP : " host_ip
                                break
                                ;;
                            *)
                                if [[ "$host_ip_list" =~ .*"$choice".* ]]; then
                                    host_ip=$choice
                                    break
                                fi
                                ;;
                        esac
                    done

                    echo "#### Backroll front configuration ####"
                    echo "Which protocol the Backroll front will be reached by ?"
                    select protocol in http https; do
                        case $protocol in
                            http|https)
                                front_url=$protocol://$host_ip
                                break
                                ;;
                        esac
                    done

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
                                [[ "$choice" == "$provided_db" ]] && backroll_db=defined

                                local action=
                                db_address=database
                                db_port=3306
                                case $choice in
                                    "$provided_db")
                                        action="Define new"
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
                                read -r -p "$action MariaDB database name (backroll) : " db_name
                                db_name=${db_name:-backroll}
                                read -r -p "$action MariaDB database username (backroll) : " db_user_name
                                db_user_name=${db_user_name:-backroll}
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
                                [[ "$choice" == "$provided_sso" ]] && backroll_sso=defined
                                break
                                ;;
                        esac
                    done

                    sso_client_secret=$(date | md5sum)
                    sso_client_secret=${sso_client_secret// /}
                    sso_client_secret=${sso_client_secret//-/}

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

                    sso_base_url="http://$host_ip:8081"
                    if [[ "$backroll_sso" == "" ]]; then
                        echo "#### Existing Keycloak configuration ####"
                        read -r -p "Enter existing Keyclock url (ex : http://localhost:8080) : " sso_base_url
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

            export backroll_db
            export backroll_mode
            export backroll_sso
            export db_address
            export db_name
            export db_port
            export db_root_password
            export db_user_name
            export db_user_password
            export flower_password
            export flower_user
            export front_url
            export sso_admin_name
            export sso_admin_password
            export sso_base_url
            export sso_client_secret
            export sso_user_name
            export sso_user_password

            for template_path in $(find . -wholename "*/template.*" 2>/dev/null); do
                local path="${template_path/template./@$backroll_mode.}"

                envsubst < "$template_path" > "$path"
            done

            if [[ "$backroll_mode" != dev ]] && [[ "$backroll_sso" == "" ]]; then
                read -r -p "Enter existing Keyclock realm (master): " keycloak_realm
                local keycloak_realm="${keycloak_realm:=master}"
                read -r -p "Enter existing Keyclock admin client_id (admin-cli) : " admin_client_id
                local admin_client_id="${admin_client_id:=admin-cli}"
                read -s -p "Enter existing Keyclock admin client_secret : " admin_client_secret
                echo
                local token=$(curl -s -X POST "$sso_base_url/realms/$keycloak_realm/protocol/openid-connect/token" \
                    -H "Content-Type: application/x-www-form-urlencoded" \
                    -d "grant_type=client_credentials&client_id=$admin_client_id&client_secret=$admin_client_secret" \
                    | grep -oP '"access_token":"\K[^"]+')

                curl -X POST "$sso_base_url/admin/realms" \
                    -H "Content-Type: application/json" \
                    -H "Authorization: Bearer $token" \
                    -d "$(cat sso/@staging.realm.json)"
            fi
            ;;
        *)
            echo "Choose dev, staging or prod." >&2
            return 1
            ;;
    esac
}

# Environment
bash ../src/env/write_base.sh .env || return 1
bash ../src/env/get_local.sh >> .env || return 1

# Setup
if [[ "$1" != "" ]]; then
    # Using a subshell not to export local environment.
    (backroll_setup "${1#setup-}") || return 1
fi

# $dev
if source @dev.env 2>/dev/null; then
    dev="--env-file .env
         --env-file @dev.env
         -f compose.yaml
         -f compose.source.yaml
         -f compose.dev.yaml
         ${BACKROLL_DB:+ --profile database}
         ${BACKROLL_SSO:+ --profile sso}"
else
    echo "Run “source source-me.sh setup-dev” to setup dev."
fi

# $staging
if source @staging.env 2>/dev/null; then
    staging="--env-file .env
             --env-file @staging.env
             -f compose.yaml
             -f compose.source.yaml
             -f compose.staging_prod.yaml
             ${BACKROLL_DB:+ --profile database}
             ${BACKROLL_SSO:+ --profile sso}"
else
    echo "Run “source source-me.sh setup-staging” to setup staging."
fi

# $prod
if source @prod.env 2>/dev/null; then
    if git describe --tags --exact-match 2>/dev/null; then
        prod="--env-file .env
              --env-file @prod.env
              -f compose.yaml
              -f compose.staging_prod.yaml
              -f compose.prod.yaml
              ${BACKROLL_DB:+ --profile database}
              ${BACKROLL_SSO:+ --profile sso}"
    else
        prod="ERROR_VERSION_MISMATCH"
    fi
else
    echo "Run “source source-me.sh setup-prod” to setup prod."
fi

echo "
Docker Compose argument variables usage:
${dev:+  - docker compose \$dev …
}${staging:+  - docker compose \$staging …
}${prod:+  - docker compose \$prod …
}"
