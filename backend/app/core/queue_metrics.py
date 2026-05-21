from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from math import ceil
from typing import Protocol


class RedisQueueClient(Protocol):
    def llen(self, name: str) -> int: ...


@dataclass(frozen=True)
class QueueDepth:
    name: str
    pending_tasks: int


@dataclass(frozen=True)
class QueueAutoscaleSnapshot:
    redis_connected: bool
    queues: list[QueueDepth]
    total_pending_tasks: int
    target_pending_tasks_per_replica: int
    min_worker_replicas: int
    max_worker_replicas: int
    recommended_worker_replicas: int
    scale_direction: str
    generated_at: datetime
    error: str | None = None


def calculate_recommended_worker_replicas(
    total_pending_tasks: int,
    target_pending_tasks_per_replica: int,
    min_worker_replicas: int,
    max_worker_replicas: int,
) -> int:
    min_replicas = max(0, min_worker_replicas)
    max_replicas = max(min_replicas, max_worker_replicas)
    target = max(1, target_pending_tasks_per_replica)
    pending_tasks = max(0, total_pending_tasks)
    if pending_tasks == 0:
        return min_replicas
    return min(max_replicas, max(min_replicas, ceil(pending_tasks / target)))


def collect_queue_depths(client: RedisQueueClient, queue_names: list[str]) -> list[QueueDepth]:
    depths: list[QueueDepth] = []
    for queue_name in queue_names:
        pending_tasks = max(0, int(client.llen(queue_name)))
        depths.append(QueueDepth(name=queue_name, pending_tasks=pending_tasks))
    return depths


def build_queue_autoscale_snapshot(
    queues: list[QueueDepth],
    target_pending_tasks_per_replica: int,
    min_worker_replicas: int,
    max_worker_replicas: int,
    redis_connected: bool,
    error: str | None = None,
) -> QueueAutoscaleSnapshot:
    total_pending_tasks = sum(queue.pending_tasks for queue in queues)
    recommended_worker_replicas = calculate_recommended_worker_replicas(
        total_pending_tasks=total_pending_tasks,
        target_pending_tasks_per_replica=target_pending_tasks_per_replica,
        min_worker_replicas=min_worker_replicas,
        max_worker_replicas=max_worker_replicas,
    )
    if not redis_connected:
        scale_direction = "broker_unavailable"
    elif recommended_worker_replicas > min_worker_replicas:
        scale_direction = "scale_out"
    elif total_pending_tasks == 0:
        scale_direction = "scale_to_min"
    else:
        scale_direction = "hold"
    return QueueAutoscaleSnapshot(
        redis_connected=redis_connected,
        queues=queues,
        total_pending_tasks=total_pending_tasks,
        target_pending_tasks_per_replica=max(1, target_pending_tasks_per_replica),
        min_worker_replicas=max(0, min_worker_replicas),
        max_worker_replicas=max(max_worker_replicas, min_worker_replicas),
        recommended_worker_replicas=recommended_worker_replicas,
        scale_direction=scale_direction,
        generated_at=datetime.now(UTC),
        error=error,
    )


def build_unavailable_snapshot(
    queue_names: list[str],
    target_pending_tasks_per_replica: int,
    min_worker_replicas: int,
    max_worker_replicas: int,
    error: str,
) -> QueueAutoscaleSnapshot:
    return build_queue_autoscale_snapshot(
        queues=[QueueDepth(name=queue_name, pending_tasks=0) for queue_name in queue_names],
        target_pending_tasks_per_replica=target_pending_tasks_per_replica,
        min_worker_replicas=min_worker_replicas,
        max_worker_replicas=max_worker_replicas,
        redis_connected=False,
        error=error,
    )


def create_redis_queue_client(redis_url: str) -> RedisQueueClient:
    from redis import Redis

    return Redis.from_url(
        redis_url,
        decode_responses=True,
        socket_connect_timeout=1.0,
        socket_timeout=1.0,
    )


def render_prometheus_queue_metrics(snapshot: QueueAutoscaleSnapshot) -> str:
    lines = [
        "# HELP bugswarm_celery_queue_pending_tasks Pending Celery tasks by Redis queue.",
        "# TYPE bugswarm_celery_queue_pending_tasks gauge",
    ]
    for queue in snapshot.queues:
        lines.append(
            f'bugswarm_celery_queue_pending_tasks{{queue="{_escape_label(queue.name)}"}} {queue.pending_tasks}'
        )
    lines.extend(
        [
            "# HELP bugswarm_celery_queue_pending_tasks_total Total pending Celery tasks across configured queues.",
            "# TYPE bugswarm_celery_queue_pending_tasks_total gauge",
            f"bugswarm_celery_queue_pending_tasks_total {snapshot.total_pending_tasks}",
            "# HELP bugswarm_worker_recommended_replicas Recommended worker replicas from queue depth.",
            "# TYPE bugswarm_worker_recommended_replicas gauge",
            f"bugswarm_worker_recommended_replicas {snapshot.recommended_worker_replicas}",
            "# HELP bugswarm_worker_autoscale_target_pending_tasks_per_replica Queue depth target per worker replica.",
            "# TYPE bugswarm_worker_autoscale_target_pending_tasks_per_replica gauge",
            (
                "bugswarm_worker_autoscale_target_pending_tasks_per_replica "
                f"{snapshot.target_pending_tasks_per_replica}"
            ),
            "# HELP bugswarm_worker_autoscale_min_replicas Minimum worker replicas.",
            "# TYPE bugswarm_worker_autoscale_min_replicas gauge",
            f"bugswarm_worker_autoscale_min_replicas {snapshot.min_worker_replicas}",
            "# HELP bugswarm_worker_autoscale_max_replicas Maximum worker replicas.",
            "# TYPE bugswarm_worker_autoscale_max_replicas gauge",
            f"bugswarm_worker_autoscale_max_replicas {snapshot.max_worker_replicas}",
            "# HELP bugswarm_redis_connected Redis broker connectivity for queue-depth metrics.",
            "# TYPE bugswarm_redis_connected gauge",
            f"bugswarm_redis_connected {1 if snapshot.redis_connected else 0}",
        ]
    )
    return "\n".join(lines) + "\n"


def _escape_label(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')
