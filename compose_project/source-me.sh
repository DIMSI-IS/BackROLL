# Intented to be run with the bash source command.

backroll_setup() {
    backroll_mode=$1
    case $backroll_mode in
        staging|prod)
            # The files of an installation hold the keys that decrypt its database: writing them again with new
            # keys makes the secrets unreadable and can point the API to an empty database.
            if [[ -e "@$backroll_mode.env" ]]; then
                echo "@$backroll_mode.env already exists: this BackROLL is already set up." >&2
                echo "Running the setup again generates new keys and overwrites the passwords and the keys of this installation." >&2
                echo "To update BackROLL, do not run the setup again: pull the new version and recreate the containers." >&2
                read -r -p "To overwrite anyway, type: overwrite " response
                if [[ "$response" != "overwrite" ]]; then
                    echo "Nothing was changed." >&2
                    return 1
                fi
            fi
            ;;
    esac
    case $backroll_mode in
        dev|staging|prod)
            # Unset variables.
            backroll_db=

            case $backroll_mode in
                dev)
                    backroll_db=defined

                    flower_user=
                    flower_password=
                    db_root_password=root
                    db_address=database
                    db_port=3306
                    db_name=backroll
                    db_user_name=backroll
                    db_user_password=backroll
                    jwt_secret=dev-only-secret-never-use-in-production-0123456789
                    secrets_key=dev-only-secrets-key-never-use-in-production-0123456789
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

                    # Secret used to sign the login tokens.
                    jwt_secret=$(openssl rand -hex 32)
                    # Key that encrypts the secrets of the database, apart from the one of the tokens: changing one
                    # does not break the other.
                    secrets_key=$(openssl rand -hex 32)
                    ;;
            esac

            export backroll_db
            export backroll_mode
            export db_address
            export db_name
            export db_port
            export db_root_password
            export db_user_name
            export db_user_password
            export flower_password
            export flower_user
            export front_url
            export jwt_secret
            export secrets_key

            for template_path in $(find . -wholename "*/template.*" 2>/dev/null); do
                local path="${template_path/template./@$backroll_mode.}"

                envsubst < "$template_path" > "$path"
            done

            ;;
        *)
            echo "Choose dev, staging or prod." >&2
            return 1
            ;;
    esac
}

# Environment
bash ../src/env/get_read_only.sh > .env || return 1
bash ../src/env/get_default.sh >> .env || return 1
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
         ${BACKROLL_DB:+ --profile database}"
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
             ${BACKROLL_DB:+ --profile database}"
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
              ${BACKROLL_DB:+ --profile database}"
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
