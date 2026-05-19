from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

AgentType = Literal["explorer", "form", "navigation", "chaos", "visual", "auth", "regression"]
ViewportName = Literal["desktop", "mobile", "tablet"]
TestIntensity = Literal["low", "medium", "high"]
ConsensusMode = Literal["majority_vote", "strict_unanimous", "rule_weighted"]


class StartTestRunRequest(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    agent_count: int = Field(default=3, ge=1, le=8)
    max_depth: int = Field(default=3, ge=1, le=10)
    max_duration_minutes: int = Field(default=30, ge=1, le=240)
    test_intensity: TestIntensity = "medium"
    agent_types: list[AgentType] = Field(default_factory=lambda: ["explorer"], min_length=1)
    viewports: list[ViewportName] = Field(default_factory=lambda: ["desktop"], min_length=1)
    llm_council_enabled: bool = True
    llm_providers: list[str] = Field(default_factory=lambda: ["groq", "gptoss", "gemini"])
    llm_consensus_mode: ConsensusMode = "majority_vote"
    auth_profile_id: UUID | None = None
    safe_mode: bool = True


class StartTestRunResponse(BaseModel):
    test_run_id: UUID
    status: str


class AgentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    agent_type: str
    status: str
    browser: str
    viewport_width: int | None
    viewport_height: int | None
    current_url: str | None
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None
    created_at: datetime


class DiscoveredPageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    url: str
    title: str | None
    status_code: int | None
    page_type: str | None
    forms_count: int | None
    links_count: int | None
    buttons_count: int | None
    first_seen_at: datetime
    last_seen_at: datetime


class TestRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    name: str
    status: str
    agent_count: int
    max_depth: int
    max_duration_minutes: int
    test_intensity: str
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    summary: dict[str, Any] | None
    agents: list[AgentRead] = Field(default_factory=list)
    discovered_pages: list[DiscoveredPageRead] = Field(default_factory=list)
    discovered_pages_count: int = 0
    agent_steps_count: int = 0
    browser_logs_count: int = 0
    network_logs_count: int = 0
    bugs_count: int = 0


class TestRunListResponse(BaseModel):
    test_runs: list[TestRunRead]
