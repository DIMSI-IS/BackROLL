celery -A app.finalized.celery beat -S redbeat.RedBeatScheduler --loglevel=info
