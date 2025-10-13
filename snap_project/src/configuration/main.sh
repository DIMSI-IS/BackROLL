# Intented to be run with the bash source command.

root_path="${SNAP:+$SNAP/app/configuration}"
# To test this script outside the snap.
root_path="${root_path:-.}"

read_configuration() {
    cat "$root_path/$1.env" | grep -E "[A-Z_]+="
}

get_name() {
    echo "${1%%=*}"
}

get_value() {
    echo "${1#*=}"
}

set_variable() {
    declare -gx "$1=$2"
}

load_configuration() {
    while read line; do
        set_variable "$(get_name "$line")" "$(get_value "$line")"
    done <<< "$(read_configuration read_only)"

    while read line; do
        local name="$(get_name "$line")"
        local default="$(get_value "$line")"

        local lower_name="${name,,}"
        local upper_name="${name^^}"

        local snap_name="${lower_name//_/.}"
        local env_name="${upper_name//./_}"

        local value
        # To test this outside the snap.
        ! test -z "$SNAP" && value="$(snapctl get "$snap_name")"
        if test -z "$value"; then
            value="$default"
            ! test -z "$SNAP" && snapctl set "$snap_name=$value"
        fi

        set_variable "$env_name" "$value"
    done <<< "$(read_configuration default)"
}

check_configuration() {
    echo "TODO implement the configuration check."
}

load_configuration
check_configuration
