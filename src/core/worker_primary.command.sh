bash ssh_setup.sh
celery -A app.celery worker -n worker -Q default --concurrency=4 --loglevel=info
