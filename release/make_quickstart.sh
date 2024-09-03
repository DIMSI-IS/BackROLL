# Makes the quickstart script targeting the current release.
# The current commit must be the current release.

tag_name=$(git describe --tags --exact-match) && \
cat <<HEREDOC > quickstart.sh
# Intented to be run with the bash source command.
# Do not use “set -e” because it will exit the user shell.

git clone --single-branch --branch main https://github.com/DIMSI-IS/backroll.git BackROLL && \\
cd BackROLL && \\
git checkout "$tag_name" && \\
cd compose_project && \\
source source-me.sh prod && \\
docker compose \$prod up
HEREDOC
