web: mkdir -p /logs && gunicorn config.asgi:application \
  -k uvicorn.workers.UvicornWorker \
  --workers 2 \
  --threads 4 \
  --bind 0.0.0.0:$PORT \
  --access-logfile /logs/gunicorn_access.log \
  --error-logfile /logs/gunicorn_error.log