from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import PlainTextResponse

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.queue import celery_app
from app.core.queue_metrics import (
    QueueAutoscaleSnapshot,
    build_queue_autoscale_snapshot,
    build_unavailable_snapshot,
    collect_queue_depths,
    create_redis_queue_client,
    render_prometheus_queue_metrics,
)
from app.models import User
from app.schemas.system import (
    LLMProviderStatus,
    QueueAutoscaleStatusResponse,
    QueueDepthResponse,
    RetentionCleanupRequest,
    RetentionCleanupResponse,
    RetentionPolicyResponse,
    SystemConfigResponse,
)

router = APIRouter()


@router.get("/config", response_model=SystemConfigResponse)
def get_system_config() -> SystemConfigResponse:
    providers = [
        LLMProviderStatus(
            provider_key="groq",
            model=settings.groq_model,
            configured=bool(settings.groq_api_key),
            enabled=bool(settings.groq_api_key),
            free_mode=settings.ai_free_mode,
        ),
        LLMProviderStatus(
            provider_key="openrouter",
            model=settings.openrouter_model,
            base_url=settings.openrouter_base_url,
            configured=bool(settings.openrouter_api_key),
            enabled=bool(settings.openrouter_api_key),
            free_mode=settings.ai_free_mode,
        ),
        LLMProviderStatus(
            provider_key="gptoss",
            model=settings.gptoss_model,
            base_url=settings.gptoss_base_url,
            configured=bool(settings.gptoss_base_url),
            enabled=bool(settings.gptoss_base_url),
            free_mode=True,
        ),
        LLMProviderStatus(
            provider_key="gemini",
            model=settings.gemini_model,
            configured=bool(settings.gemini_api_key),
            enabled=bool(settings.gemini_api_key),
            free_mode=settings.ai_free_mode,
        ),
    ]
    return SystemConfigResponse(
        environment=settings.app_env,
        ai_free_mode=settings.ai_free_mode,
        providers=providers,
        default_agent_count=settings.default_agent_count,
        default_max_depth=settings.default_max_depth,
    )


@router.get("/retention", response_model=RetentionPolicyResponse)
def get_retention_policy() -> RetentionPolicyResponse:
    return RetentionPolicyResponse(
        screenshot_days=settings.screenshot_retention_days,
        trace_days=settings.trace_retention_days,
        report_days=settings.report_retention_days,
        browser_log_days=settings.browser_log_retention_days,
        network_log_days=settings.network_log_retention_days,
    )


@router.get("/queue", response_model=QueueAutoscaleStatusResponse)
def get_queue_autoscale_status() -> QueueAutoscaleStatusResponse:
    return _queue_status_response(_read_queue_autoscale_snapshot())


@router.get("/queue/metrics", response_class=PlainTextResponse)
def get_queue_prometheus_metrics() -> PlainTextResponse:
    snapshot = _read_queue_autoscale_snapshot()
    return PlainTextResponse(
        render_prometheus_queue_metrics(snapshot),
        media_type="text/plain; version=0.0.4",
    )


@router.post("/retention/cleanup", response_model=RetentionCleanupResponse)
def queue_retention_cleanup(
    payload: RetentionCleanupRequest,
    current_user: User = Depends(get_current_user),
) -> RetentionCleanupResponse:
    del current_user
    job = payload.model_dump(exclude_none=True)
    try:
        task = celery_app.send_task("bugswarm.cleanup_retention", args=[job])
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Retention cleanup could not be queued. Check that Redis and the worker are running.",
        ) from exc
    return RetentionCleanupResponse(queued=True, task_id=task.id, dry_run=payload.dry_run)


def _read_queue_autoscale_snapshot() -> QueueAutoscaleSnapshot:
    queue_names = settings.celery_queue_names
    try:
        client = create_redis_queue_client(settings.redis_url)
        depths = collect_queue_depths(client, queue_names)
    except Exception as exc:
        return build_unavailable_snapshot(
            queue_names=queue_names,
            target_pending_tasks_per_replica=settings.queue_autoscale_target_pending_per_replica,
            min_worker_replicas=settings.queue_autoscale_min_worker_replicas,
            max_worker_replicas=settings.queue_autoscale_max_worker_replicas,
            error=str(exc),
        )
    return build_queue_autoscale_snapshot(
        queues=depths,
        target_pending_tasks_per_replica=settings.queue_autoscale_target_pending_per_replica,
        min_worker_replicas=settings.queue_autoscale_min_worker_replicas,
        max_worker_replicas=settings.queue_autoscale_max_worker_replicas,
        redis_connected=True,
    )


def _queue_status_response(snapshot: QueueAutoscaleSnapshot) -> QueueAutoscaleStatusResponse:
    return QueueAutoscaleStatusResponse(
        redis_connected=snapshot.redis_connected,
        queues=[
            QueueDepthResponse(name=queue.name, pending_tasks=queue.pending_tasks)
            for queue in snapshot.queues
        ],
        total_pending_tasks=snapshot.total_pending_tasks,
        target_pending_tasks_per_replica=snapshot.target_pending_tasks_per_replica,
        min_worker_replicas=snapshot.min_worker_replicas,
        max_worker_replicas=snapshot.max_worker_replicas,
        recommended_worker_replicas=snapshot.recommended_worker_replicas,
        scale_direction=snapshot.scale_direction,
        generated_at=snapshot.generated_at,
        error=snapshot.error,
    )
