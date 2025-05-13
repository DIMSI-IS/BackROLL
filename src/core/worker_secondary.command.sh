bash ssh_setup.sh
# TODO app.applications.finalized.celery
celery -A app.register.celery worker -n worker2 -Q backup_tasks --concurrency=2 --loglevel=info
