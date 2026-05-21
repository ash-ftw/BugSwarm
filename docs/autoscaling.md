# Queue-Depth Autoscaling

BugSwarm exposes Celery queue depth in two forms:

- `GET /api/system/queue` returns JSON for the dashboard and operational checks.
- `GET /api/system/queue/metrics` returns Prometheus text metrics.

The backend reads the configured Redis list names from `CELERY_QUEUE_NAMES`, defaulting to `celery`. The recommendation uses:

- `QUEUE_AUTOSCALE_TARGET_PENDING_PER_REPLICA`
- `QUEUE_AUTOSCALE_MIN_WORKER_REPLICAS`
- `QUEUE_AUTOSCALE_MAX_WORKER_REPLICAS`

The recommended replica count is `ceil(total_pending_tasks / target_pending_per_replica)` clamped between the configured minimum and maximum. When Redis is unavailable, the JSON endpoint reports `redis_connected: false`, and the metrics endpoint emits `bugswarm_redis_connected 0`.

## Prometheus Metrics

The backend service is annotated for scraping `/api/system/queue/metrics`. The main gauges are:

- `bugswarm_celery_queue_pending_tasks{queue="celery"}`
- `bugswarm_celery_queue_pending_tasks_total`
- `bugswarm_worker_recommended_replicas`
- `bugswarm_worker_autoscale_target_pending_tasks_per_replica`
- `bugswarm_worker_autoscale_min_replicas`
- `bugswarm_worker_autoscale_max_replicas`
- `bugswarm_redis_connected`

## KEDA Production Scaling

The optional manifests in `k8s/production` assume the application deployment already exists in the `bugswarm` namespace and KEDA is installed in the cluster.

```powershell
kubectl apply -k .\k8s\production
```

`worker-keda-scaledobject.yaml` scales `deployment/bugswarm-worker` from Redis list length. Keep `listName`, `listLength`, `minReplicaCount`, and `maxReplicaCount` aligned with the backend autoscale environment variables so the dashboard recommendation matches the production scaler.

The default Minikube deployment keeps the CPU-based HPA for a low-dependency local path. Do not run the CPU HPA and KEDA ScaledObject against the same worker deployment in production unless you intentionally want multiple autoscalers controlling the same replica field.
