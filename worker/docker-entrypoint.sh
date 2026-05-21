#!/usr/bin/env sh
set -eu

if [ -n "${WORKER_AUTOSCALE:-}" ]; then
  set -- --autoscale="${WORKER_AUTOSCALE}"
else
  set -- --concurrency="${WORKER_CONCURRENCY:-4}"
fi

exec celery -A bugswarm_worker.tasks worker --loglevel="${CELERY_LOG_LEVEL:-INFO}" "$@"
