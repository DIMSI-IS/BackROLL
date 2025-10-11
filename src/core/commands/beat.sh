celery -A app.finalized.celery_app beat -S redbeat.RedBeatScheduler --loglevel=info
