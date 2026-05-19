from __future__ import annotations

from celery import Celery

from bugswarm_worker.config import settings

celery_app = Celery(
    "bugswarm-worker",
    broker=settings.redis_url,
    backend=settings.redis_url,
)
