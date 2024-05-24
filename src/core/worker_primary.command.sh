eval "$(ssh-agent -s)"
ssh-add /root/.ssh/id_*
celery -A app.celery worker -n worker -Q default --concurrency=4 --loglevel=info
