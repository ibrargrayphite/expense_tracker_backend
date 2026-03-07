web: gunicorn config.asgi:application -k uvicorn.workers.UvicornWorker --workers 2 --threads 4 --bind 0.0.0.0:8000
worker: celery -A config worker -l info
beat: celery -A config beat -l info
