set -e

git clone --single-branch --branch main https://github.com/DIMSI-IS/backroll.git BackROLL
cd BackROLL
git checkout $(git describe --tags --abbrev=0)
