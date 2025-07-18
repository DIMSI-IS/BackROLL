# Intented to be run with the bash source command.

backroll_setup() {
    local backroll_mode=$1
    case $backroll_mode in
        dev|staging|prod)
            # Unset variables.
            local backroll_db=
            local backroll_sso=

            # Shared or default values
            local backroll_host_user=$(echo "${USERNAME:-${USER:-someone}}" | sed 's/\./-/g')
            local backroll_hostname=$HOSTNAME

            case $backroll_mode in
                dev)
                    local flower_user=
                    local flower_password=
                    local db_root_password=root
                    local db_address=database
                    local db_port=3306
                    local db_name=backroll
                    local db_user_name=backroll
                    local db_user_password=backroll
                    local sso_admin_name=admin
                    local sso_admin_password=admin
                    local sso_base_url=http://sso:8080
                    local sso_client_secret=e7cbb6ae88ce7cd7cf3b104a972d08ed
                    local sso_user_name=developer
                    local sso_user_password=developer
                    local api_address=api
                    local front_url=http://front:8080
                    ;;
                staging|prod)
                    case $backroll_mode in
                        prod)
                            if ! git describe --tags --exact-match 2>/dev/null; then
                                read -r -p "You are not on a release commit. Run version mismatch protection ? " response
                                if [[ "$response" != "I know that prod will fail." ]]; then
                                    echo "Running version mismatch protection…"
                                    git checkout $(git describe --tags --abbrev=0) || return $?
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
                    local api_address=$host_ip
                    local front_address=$host_ip

                    local front_port=
                    case $backroll_mode in
                        staging)
                            front_port=8080
                            ;;
                    esac

                    echo "#### Backroll front configuration ####"
                    echo "Which protocol the Backroll front will be reached by ?"
                    select protocol in http https; do
                        case $protocol in
                            http|https)
                                local front_url=$protocol://$front_address${front_port:+:$front_port}
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
                                [[ "$choice" == "$provided_db" ]] && local backroll_db=defined

                                local action=
                                local db_address=database
                                local db_port=3306
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

                    local sso_client_secret=$(date | md5sum)
                    local sso_client_secret=(${sso_client_secret// / })
                    local sso_client_secret=${sso_client_secret[0]}

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

                    local sso_base_url="http://$host_ip:8081"
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

            for template_path in $(find . -wholename "*/template.*" 2>/dev/null); do
                local path="${template_path/template./@$backroll_mode.}"

                cp "$template_path" "$path"

                # TODO Better use envsubst ?
                for var_name in backroll_host_user \
                                backroll_hostname \
                                backroll_mode \
                                flower_user \
                                flower_password \
                                backroll_db \
                                backroll_sso \
                                db_root_password \
                                db_address \
                                db_port \
                                db_name \
                                db_user_name \
                                db_user_password \
                                sso_admin_name \
                                sso_admin_password \
                                sso_base_url \
                                sso_client_secret \
                                sso_user_name \
                                sso_user_password \
                                api_address \
                                front_url \
                                ;
                do
                    sed -i 's|_'"$var_name"'|'"${!var_name}"'|' "$path"
                done
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
                    -d "$(cat sso/realm.json)"
            fi
            ;;
        *)
            echo "Choose dev, staging or prod." 1>&2
            return 1
            ;;
    esac
}

# Setup
if [[ "$1" != "" ]]; then
    backroll_setup "${1#setup-}" || return $?
fi

# Context
backroll_version=$(git describe --tags)
cat <<HEREDOC > .env
BACKROLL_VERSION=$backroll_version
HEREDOC

# $dev
if source backroll/@dev.env 2>/dev/null; then
    dev="--env-file backroll/@dev.env
         --env-file .env
         -f compose.yaml
         -f compose.source.yaml
         -f compose.dev.yaml
         --profile database
         --profile sso"
else
    echo "Run “source source-me.sh setup-dev” to setup dev."
fi

# $staging
if source backroll/@staging.env 2>/dev/null; then
    staging="--env-file backroll/@staging.env
             --env-file .env
             -f compose.yaml
             -f compose.source.yaml
             -f compose.staging_prod.yaml
             -f compose.staging.yaml
             ${BACKROLL_DB:+ --profile database}
             ${BACKROLL_SSO:+ --profile sso}"
else
    echo "Run “source source-me.sh setup-staging” to setup staging."
fi

# $prod
if source backroll/@prod.env 2>/dev/null; then
    if git describe --tags --exact-match 2>/dev/null; then
        prod="--env-file backroll/@prod.env
            --env-file .env
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
