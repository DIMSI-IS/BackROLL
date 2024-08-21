bash ssh_setup.sh
/app/venv/bin/celery -A app.celery worker -n worker2 -Q backup_tasks --concurrency=2 --loglevel=info
