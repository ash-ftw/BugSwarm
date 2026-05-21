from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

BugStatus = Literal["open", "triaged", "resolved", "ignored"]


class BugArtifactRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    bug_id: UUID
    artifact_type: str
    file_path: str
    mime_type: str | None
    file_size_bytes: int | None
    label: str | None
    created_at: datetime


class ReplayStepRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    bug_id: UUID
    step_order: int
    action_type: str
    selector: str | None
    selector_hint: str | None
    input_value: str | None
    url: str | None
    expected_result: str | None
    created_at: datetime


class BrowserLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    log_level: str | None
    message: str | None
    source_url: str | None
    line_number: int | None
    column_number: int | None
    created_at: datetime


class NetworkLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    request_url: str
    method: str | None
    status_code: int | None
    resource_type: str | None
    failure_text: str | None
    duration_ms: int | None
    created_at: datetime


class BugRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    test_run_id: UUID | None
    agent_id: UUID | None
    test_case_id: UUID | None
    title: str
    description: str | None
    category: str
    severity: str
    status: str
    affected_url: str | None
    expected_result: str | None
    actual_result: str | None
    ai_summary: str | None
    suggested_fix: str | None
    ai_consensus_status: str | None
    ai_confidence: float | None
    reasoning_session_id: UUID | None
    fingerprint: str | None
    first_seen_at: datetime
    last_seen_at: datetime
    created_at: datetime
    artifacts: list[BugArtifactRead] = Field(default_factory=list)
    replay_steps: list[ReplayStepRead] = Field(default_factory=list)
    browser_logs: list[BrowserLogRead] = Field(default_factory=list)
    network_logs: list[NetworkLogRead] = Field(default_factory=list)


class BugListResponse(BaseModel):
    bugs: list[BugRead]


class BugUpdate(BaseModel):
    status: BugStatus | None = None
    severity: Literal["critical", "high", "medium", "low"] | None = None
    ai_summary: str | None = Field(default=None, max_length=2000)
    suggested_fix: str | None = Field(default=None, max_length=2000)


class ReportRead(BaseModel):
    report_type: str
    content: dict[str, Any]


class ReplayResponse(BaseModel):
    bug_id: UUID
    status: str
    task_id: str | None = None


class ReplayHistoryResponse(BaseModel):
    bug_id: UUID
    replay_steps: list[ReplayStepRead]
    attempts: list[dict[str, Any]] = Field(default_factory=list)


class PlaywrightScriptResponse(BaseModel):
    bug_id: UUID
    script: str


class BugValidationResponse(BaseModel):
    bug_id: UUID
    status: str
    task_id: str | None = None


class BugValidationHistoryResponse(BaseModel):
    bug_id: UUID
    sessions: list[dict[str, Any]] = Field(default_factory=list)
