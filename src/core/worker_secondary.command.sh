eval "$(ssh-agent -s)"
ssh-add /root/.ssh/id
celery -A app.celery worker -n worker2 -Q backup_tasks --concurrency=2 --loglevel=info
