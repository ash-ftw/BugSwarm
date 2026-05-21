from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.queue_metrics import (
    QueueDepth,
    build_queue_autoscale_snapshot,
    calculate_recommended_worker_replicas,
    render_prometheus_queue_metrics,
)


class QueueMetricsTests(unittest.TestCase):
    def test_recommended_replicas_are_clamped_to_limits(self) -> None:
        self.assertEqual(
            calculate_recommended_worker_replicas(
                total_pending_tasks=0,
                target_pending_tasks_per_replica=4,
                min_worker_replicas=1,
                max_worker_replicas=10,
            ),
            1,
        )
        self.assertEqual(
            calculate_recommended_worker_replicas(
                total_pending_tasks=9,
                target_pending_tasks_per_replica=4,
                min_worker_replicas=1,
                max_worker_replicas=10,
            ),
            3,
        )
        self.assertEqual(
            calculate_recommended_worker_replicas(
                total_pending_tasks=100,
                target_pending_tasks_per_replica=4,
                min_worker_replicas=1,
                max_worker_replicas=6,
            ),
            6,
        )

    def test_snapshot_marks_scale_out_when_queue_exceeds_min_capacity(self) -> None:
        snapshot = build_queue_autoscale_snapshot(
            queues=[QueueDepth(name="celery", pending_tasks=9)],
            target_pending_tasks_per_replica=4,
            min_worker_replicas=1,
            max_worker_replicas=10,
            redis_connected=True,
        )

        self.assertEqual(snapshot.total_pending_tasks, 9)
        self.assertEqual(snapshot.recommended_worker_replicas, 3)
        self.assertEqual(snapshot.scale_direction, "scale_out")

    def test_prometheus_metrics_include_queue_and_recommendation(self) -> None:
        snapshot = build_queue_autoscale_snapshot(
            queues=[QueueDepth(name='celery"prod', pending_tasks=5)],
            target_pending_tasks_per_replica=4,
            min_worker_replicas=1,
            max_worker_replicas=10,
            redis_connected=True,
        )

        metrics = render_prometheus_queue_metrics(snapshot)
        self.assertIn('bugswarm_celery_queue_pending_tasks{queue="celery\\"prod"} 5', metrics)
        self.assertIn("bugswarm_worker_recommended_replicas 2", metrics)
        self.assertIn("bugswarm_redis_connected 1", metrics)


if __name__ == "__main__":
    unittest.main()
