load_configuration() {
    while read line; do
        local name="${line%%=*}"
        local default="${line#*=}"

        local lower_name="${name,,}"
        local upper_name="${name^^}"

        local snap_name="${lower_name//_/.}"
        local env_name="${upper_name//./_}"

        local value="$(snapctl get "$snap_name")"
        if test -z "$value"; then
            value="$default"
            snapctl set "$snap_name=$value"
        fi

        # TODO -x to export.
        declare -g "$env_name=$value"
    done < "$SNAP/configuration/default.txt"
}

check_configuration() {
    echo "TODO implement the configuration check."
}

load_configuration
check_configuration
