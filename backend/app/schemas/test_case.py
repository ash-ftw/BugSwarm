from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TestStepRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    test_case_id: UUID
    step_order: int
    action_type: str
    selector_hint: str | None
    selector_resolved: str | None
    input_value: str | None
    expected_observation: str | None
    timeout_ms: int | None
    created_at: datetime


class TestCaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    test_run_id: UUID | None
    name: str
    description: str | None
    source: str
    priority: str
    status: str
    expected_result: str | None
    ai_prompt_hash: str | None
    created_at: datetime
    steps: list[TestStepRead] = Field(default_factory=list)


class LLMModelResponseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    reasoning_session_id: UUID
    provider_key: str
    model_name: str
    status: str
    confidence: float | None
    vote: str | None
    rationale_summary: str | None
    output: dict[str, Any] | None
    error_message: str | None
    latency_ms: int | None
    token_usage: dict[str, Any] | None
    created_at: datetime


class LLMReasoningSessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    test_run_id: UUID | None
    bug_id: UUID | None
    task_type: str
    prompt_fingerprint: str
    consensus_status: str
    consensus_mode: str
    final_rationale: str | None
    requires_human_review: bool
    session_metadata: dict[str, Any] | None
    created_at: datetime
    model_responses: list[LLMModelResponseRead] = Field(default_factory=list)


class TestCaseListResponse(BaseModel):
    test_cases: list[TestCaseRead]
    reasoning_sessions: list[LLMReasoningSessionRead] = Field(default_factory=list)
