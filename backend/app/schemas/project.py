from __future__ import annotations

from datetime import datetime
from typing import Literal
from urllib.parse import urlparse
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

ProviderKey = Literal["groq", "gptoss", "gemini", "openrouter"]
ScopeType = Literal["allow", "exclude"]
ProjectStatus = Literal["active", "archived"]
TestIntensity = Literal["low", "medium", "high"]
ConsensusMode = Literal["majority_vote", "strict_unanimous", "rule_weighted"]


class ProjectScopeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    scope_type: ScopeType
    pattern: str
    created_at: datetime


class LLMProviderConfigRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    provider_key: ProviderKey
    model_name: str
    base_url: str | None
    is_enabled: bool
    is_free_mode: bool
    timeout_seconds: int
    max_retries: int


class ProjectBase(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    description: str | None = Field(default=None, max_length=2000)
    base_url: str
    default_max_depth: int = Field(default=3, ge=1, le=10)
    default_agent_count: int = Field(default=3, ge=1, le=8)
    default_test_intensity: TestIntensity = "medium"
    llm_council_enabled: bool = True
    llm_consensus_mode: ConsensusMode = "majority_vote"
    free_ai_mode: bool = True
    allowed_paths: list[str] = Field(default_factory=list)
    excluded_paths: list[str] = Field(default_factory=list)

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        cleaned = value.strip().rstrip("/")
        parsed = urlparse(cleaned)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Base URL must be a valid http or https URL.")
        return cleaned

    @field_validator("allowed_paths", "excluded_paths")
    @classmethod
    def strip_patterns(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item.strip()]


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=180)
    description: str | None = Field(default=None, max_length=2000)
    base_url: str | None = None
    status: ProjectStatus | None = None
    default_max_depth: int | None = Field(default=None, ge=1, le=10)
    default_agent_count: int | None = Field(default=None, ge=1, le=8)
    default_test_intensity: TestIntensity | None = None
    llm_council_enabled: bool | None = None
    llm_consensus_mode: ConsensusMode | None = None
    free_ai_mode: bool | None = None
    allowed_paths: list[str] | None = None
    excluded_paths: list[str] | None = None

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip().rstrip("/")
        parsed = urlparse(cleaned)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Base URL must be a valid http or https URL.")
        return cleaned

    @field_validator("allowed_paths", "excluded_paths")
    @classmethod
    def strip_patterns(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        return [item.strip() for item in value if item.strip()]


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    name: str
    description: str | None
    base_url: str
    status: str
    default_max_depth: int
    default_agent_count: int
    default_test_intensity: str
    llm_council_enabled: bool
    llm_consensus_mode: str
    free_ai_mode: bool
    scopes: list[ProjectScopeRead] = Field(default_factory=list)
    llm_provider_configs: list[LLMProviderConfigRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class ProjectListResponse(BaseModel):
    projects: list[ProjectRead]
