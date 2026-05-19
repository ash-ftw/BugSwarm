from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from redis import Redis

from bugswarm_worker.config import settings

_redis_client = Redis.from_url(settings.redis_url, decode_responses=True)


def test_run_event_channel(test_run_id: str) -> str:
    return f"bugswarm:test-runs:{test_run_id}:events"


def publish_event(test_run_id: str, event: str, payload: dict[str, Any]) -> None:
    message = {
        "event": event,
        "test_run_id": test_run_id,
        "created_at": datetime.now(UTC).isoformat(),
        **payload,
    }
    try:
        _redis_client.publish(test_run_event_channel(test_run_id), json.dumps(message, ensure_ascii=True))
    except Exception:
        pass
