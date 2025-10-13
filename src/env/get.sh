read_only=$(cat <<HEREDOC
# TODO Not in snap :
BACKROLL_HOSTNAME=$HOSTNAME
BACKROLL_HOST_USER=$(echo "${USERNAME:-${USER:-someone}}" | sed 's/\./-/g')
# …not in snap.
BACKROLL_VERSION=$(git describe --tags)

BORG_UNKNOWN_UNENCRYPTED_REPO_ACCESS_IS_OK=yes
FLOWER_UNAUTHENTICATED_API=true
HEREDOC
)

default=$(cat <<HEREDOC
DEFAULT_USER_NAME=admin
DEFAULT_USER_PASSWORD=admin

FLOWER_PASSWORD=
FLOWER_USER=

FRONT_URL=

OPENID_CLIENT_API_ID=backroll-api
OPENID_CLIENT_API_SECRET=
OPENID_CLIENT_UI_ID=backroll-front
OPENID_ISSUER=
OPENID_REALM=backroll
HEREDOC
)

case "$#" in
    1)
        cat <<HEREDOC > "$1"
$read_only
$default
HEREDOC
        ;;
    2)
        cat <<HEREDOC > "$1"
$read_only
HEREDOC
        cat <<HEREDOC > "$2"
$default
HEREDOC
        ;;
    *)
        echo "Provide <env_path> or <read_only_path> <default_path>."
        exit 1
        ;;
esac
