# The limit of simultaneous backups is a setting of the application (at most BACKUP_MAX_CONCURRENCY).
case "${BACKUP_MAX_CONCURRENCY:-8}" in
  ""|*[!0-9]*|0) echo "BACKUP_MAX_CONCURRENCY must be a positive number." >&2; exit 1;;
esac
celery -A app.finalized.celery_app worker -n worker2 -Q backup_tasks --concurrency="${BACKUP_MAX_CONCURRENCY:-8}" --loglevel=info
