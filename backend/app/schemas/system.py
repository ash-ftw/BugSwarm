from datetime import datetime

from pydantic import BaseModel, Field


class LLMProviderStatus(BaseModel):
    provider_key: str
    model: str
    configured: bool
    enabled: bool
    free_mode: bool
    base_url: str | None = None


class SystemConfigResponse(BaseModel):
    environment: str
    ai_free_mode: bool
    providers: list[LLMProviderStatus]
    default_agent_count: int
    default_max_depth: int


class RetentionPolicyResponse(BaseModel):
    screenshot_days: int
    trace_days: int
    report_days: int
    browser_log_days: int
    network_log_days: int


class RetentionCleanupRequest(BaseModel):
    dry_run: bool = False
    screenshot_days: int | None = Field(default=None, ge=1, le=3650)
    trace_days: int | None = Field(default=None, ge=1, le=3650)
    report_days: int | None = Field(default=None, ge=1, le=3650)
    browser_log_days: int | None = Field(default=None, ge=1, le=3650)
    network_log_days: int | None = Field(default=None, ge=1, le=3650)


class RetentionCleanupResponse(BaseModel):
    queued: bool
    task_id: str | None = None
    dry_run: bool


class QueueDepthResponse(BaseModel):
    name: str
    pending_tasks: int


class QueueAutoscaleStatusResponse(BaseModel):
    redis_connected: bool
    queues: list[QueueDepthResponse]
    total_pending_tasks: int
    target_pending_tasks_per_replica: int
    min_worker_replicas: int
    max_worker_replicas: int
    recommended_worker_replicas: int
    scale_direction: str
    generated_at: datetime
    error: str | None = None
