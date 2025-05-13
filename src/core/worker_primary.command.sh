bash ssh_setup.sh
# TODO app.applications.finalized.celery
celery -A app.register.celery worker -n worker -Q default --concurrency=4 --loglevel=info
