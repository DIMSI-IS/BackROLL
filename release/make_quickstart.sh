# Makes the quickstart script targeting the latest release.

# Intented to be run with the bash source command.
# Do not use “set -e” because it will exit the user shell.
cat <<HEREDOC > quickstart.sh
git clone --single-branch --branch main https://github.com/DIMSI-IS/backroll.git BackROLL && \
cd BackROLL && \
git checkout $(git describe --tags --abbrev=0) && \
cd compose_project && \
source source-me.sh prod && \
docker compose \$prod up
HEREDOC
