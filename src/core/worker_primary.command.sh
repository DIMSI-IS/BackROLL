eval "$(ssh-agent -s)"
chmod 400 /root/.ssh/id_*
ssh-add /root/.ssh/id_*
celery -A app.celery worker -n worker -Q default --concurrency=4 --loglevel=info
