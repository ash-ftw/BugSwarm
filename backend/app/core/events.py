from __future__ import annotations

import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from redis import Redis
from redis import asyncio as redis

from app.core.config import settings


def test_run_event_channel(test_run_id: UUID | str) -> str:
    return f"bugswarm:test-runs:{test_run_id}:events"


def publish_test_run_event(test_run_id: UUID | str, event: str, payload: dict[str, Any]) -> None:
    message = {
        "event": event,
        "test_run_id": str(test_run_id),
        "created_at": datetime.now(UTC).isoformat(),
        **payload,
    }
    try:
        client = Redis.from_url(settings.redis_url, decode_responses=True)
        client.publish(test_run_event_channel(test_run_id), json.dumps(message, ensure_ascii=True))
        client.close()
    except Exception:
        pass


async def subscribe_test_run_events(test_run_id: UUID | str) -> AsyncIterator[dict[str, Any]]:
    client = redis.from_url(settings.redis_url, decode_responses=True)
    pubsub = client.pubsub()
    await pubsub.subscribe(test_run_event_channel(test_run_id))
    try:
        async for message in pubsub.listen():
            if message.get("type") != "message":
                continue
            raw = message.get("data")
            if not isinstance(raw, str):
                continue
            try:
                yield json.loads(raw)
            except json.JSONDecodeError:
                yield {"event": "message", "message": raw}
    finally:
        await pubsub.unsubscribe(test_run_event_channel(test_run_id))
        await pubsub.close()
        await client.aclose()
