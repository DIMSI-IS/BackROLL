# Run this script with the "source" command.

files="$1"

echo "Loading environment: $files"
for file in $files
do
  echo "Loading $file…"
  set -o allexport
  source $file
  set +o allexport
done
