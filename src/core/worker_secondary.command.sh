eval "$(ssh-agent -s)"
chmod 400 /root/.ssh/id_*
ssh-add /root/.ssh/id_*
celery -A app.celery worker -n worker2 -Q backup_tasks --concurrency=2 --loglevel=info
