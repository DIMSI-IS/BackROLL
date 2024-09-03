# Makes the quickstart script targeting the latest release.

cat <<HEREDOC > quickstart.sh
set -e

git clone --single-branch --branch main https://github.com/DIMSI-IS/backroll.git BackROLL
cd BackROLL
git checkout $(git describe --tags --abbrev=0)

cd compose_project
source source-me.sh prod
docker compose \$prod up
HEREDOC
