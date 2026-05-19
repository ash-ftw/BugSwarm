from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.current_timestamp())


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(String(30), nullable=False, server_default="tester")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("TRUE"))
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.current_timestamp())


class Project(TimestampMixin, Base):
    __tablename__ = "projects"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    user_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    base_url: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, server_default="active")
    default_max_depth: Mapped[int] = mapped_column(Integer, nullable=False, server_default="3")
    default_agent_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="3")
    default_test_intensity: Mapped[str] = mapped_column(String(30), nullable=False, server_default="medium")
    llm_council_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("TRUE"))
    llm_consensus_mode: Mapped[str] = mapped_column(String(50), nullable=False, server_default="majority_vote")
    free_ai_mode: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("TRUE"))
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.current_timestamp())


class ProjectScope(TimestampMixin, Base):
    __tablename__ = "project_scopes"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    project_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    scope_type: Mapped[str] = mapped_column(String(30), nullable=False)
    pattern: Mapped[str] = mapped_column(Text, nullable=False)


class AuthProfile(TimestampMixin, Base):
    __tablename__ = "auth_profiles"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    project_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    auth_type: Mapped[str] = mapped_column(String(50), nullable=False)
    login_url: Mapped[str | None] = mapped_column(Text)
    username_selector: Mapped[str | None] = mapped_column(Text)
    password_selector: Mapped[str | None] = mapped_column(Text)
    submit_selector: Mapped[str | None] = mapped_column(Text)
    username_value: Mapped[str | None] = mapped_column(Text)
    encrypted_password_value: Mapped[str | None] = mapped_column(Text)
    storage_state_path: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("TRUE"))


class TestRun(TimestampMixin, Base):
    __tablename__ = "test_runs"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    project_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, server_default="queued")
    agent_count: Mapped[int] = mapped_column(Integer, nullable=False)
    max_depth: Mapped[int] = mapped_column(Integer, nullable=False)
    max_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    test_intensity: Mapped[str] = mapped_column(String(30), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_by: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), ForeignKey("users.id"))
    summary: Mapped[dict[str, Any] | None] = mapped_column(JSONB)


class LLMProviderConfig(TimestampMixin, Base):
    __tablename__ = "llm_provider_configs"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    project_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    provider_key: Mapped[str] = mapped_column(String(30), nullable=False)
    model_name: Mapped[str] = mapped_column(String(120), nullable=False)
    base_url: Mapped[str | None] = mapped_column(Text)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("TRUE"))
    is_free_mode: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("TRUE"))
    timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False, server_default="30")
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, server_default="2")
    rate_limit_policy: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.current_timestamp())


class LLMReasoningSession(TimestampMixin, Base):
    __tablename__ = "llm_reasoning_sessions"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    test_run_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), ForeignKey("test_runs.id", ondelete="CASCADE"))
    bug_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True))
    task_type: Mapped[str] = mapped_column(String(50), nullable=False)
    prompt_fingerprint: Mapped[str] = mapped_column(String(128), nullable=False)
    consensus_status: Mapped[str] = mapped_column(String(50), nullable=False)
    consensus_mode: Mapped[str] = mapped_column(String(50), nullable=False, server_default="majority_vote")
    final_rationale: Mapped[str | None] = mapped_column(Text)
    requires_human_review: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("FALSE"))
    session_metadata: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB)


class LLMModelResponse(TimestampMixin, Base):
    __tablename__ = "llm_model_responses"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    reasoning_session_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("llm_reasoning_sessions.id", ondelete="CASCADE"), nullable=False)
    provider_key: Mapped[str] = mapped_column(String(30), nullable=False)
    model_name: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, server_default="completed")
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    vote: Mapped[str | None] = mapped_column(String(40))
    rationale_summary: Mapped[str | None] = mapped_column(Text)
    output: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    error_message: Mapped[str | None] = mapped_column(Text)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    token_usage: Mapped[dict[str, Any] | None] = mapped_column(JSONB)


class Agent(TimestampMixin, Base):
    __tablename__ = "agents"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    test_run_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("test_runs.id", ondelete="CASCADE"), nullable=False)
    agent_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, server_default="queued")
    browser: Mapped[str] = mapped_column(String(50), nullable=False, server_default="chromium")
    viewport_width: Mapped[int | None] = mapped_column(Integer)
    viewport_height: Mapped[int | None] = mapped_column(Integer)
    current_url: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    error_message: Mapped[str | None] = mapped_column(Text)
    agent_metadata: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB)


class AgentStep(TimestampMixin, Base):
    __tablename__ = "agent_steps"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    agent_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target_selector: Mapped[str | None] = mapped_column(Text)
    target_text: Mapped[str | None] = mapped_column(Text)
    input_value: Mapped[str | None] = mapped_column(Text)
    url_before: Mapped[str | None] = mapped_column(Text)
    url_after: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    screenshot_artifact_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True))
    dom_snapshot_artifact_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True))
    duration_ms: Mapped[int | None] = mapped_column(Integer)


class DiscoveredPage(Base):
    __tablename__ = "discovered_pages"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    project_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    test_run_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), ForeignKey("test_runs.id", ondelete="CASCADE"))
    url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str | None] = mapped_column(Text)
    status_code: Mapped[int | None] = mapped_column(Integer)
    content_hash: Mapped[str | None] = mapped_column(Text)
    page_type: Mapped[str | None] = mapped_column(String(80))
    forms_count: Mapped[int | None] = mapped_column(Integer, server_default="0")
    links_count: Mapped[int | None] = mapped_column(Integer, server_default="0")
    buttons_count: Mapped[int | None] = mapped_column(Integer, server_default="0")
    discovered_by_agent_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), ForeignKey("agents.id"))
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.current_timestamp())
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.current_timestamp())


class PageElement(TimestampMixin, Base):
    __tablename__ = "page_elements"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    discovered_page_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("discovered_pages.id", ondelete="CASCADE"), nullable=False)
    element_type: Mapped[str] = mapped_column(String(50), nullable=False)
    selector: Mapped[str | None] = mapped_column(Text)
    role: Mapped[str | None] = mapped_column(Text)
    label: Mapped[str | None] = mapped_column(Text)
    placeholder: Mapped[str | None] = mapped_column(Text)
    text_content: Mapped[str | None] = mapped_column(Text)
    href: Mapped[str | None] = mapped_column(Text)
    is_visible: Mapped[bool | None] = mapped_column(Boolean)
    is_enabled: Mapped[bool | None] = mapped_column(Boolean)
    bounding_box: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    element_metadata: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB)


class TestCase(TimestampMixin, Base):
    __tablename__ = "test_cases"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    project_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    test_run_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), ForeignKey("test_runs.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(String(220), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(50), nullable=False, server_default="ai")
    priority: Mapped[str] = mapped_column(String(30), nullable=False, server_default="medium")
    status: Mapped[str] = mapped_column(String(40), nullable=False, server_default="generated")
    expected_result: Mapped[str | None] = mapped_column(Text)
    ai_prompt_hash: Mapped[str | None] = mapped_column(Text)


class TestStep(TimestampMixin, Base):
    __tablename__ = "test_steps"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    test_case_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("test_cases.id", ondelete="CASCADE"), nullable=False)
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    selector_hint: Mapped[str | None] = mapped_column(Text)
    selector_resolved: Mapped[str | None] = mapped_column(Text)
    input_value: Mapped[str | None] = mapped_column(Text)
    expected_observation: Mapped[str | None] = mapped_column(Text)
    timeout_ms: Mapped[int | None] = mapped_column(Integer, server_default="5000")


class Bug(TimestampMixin, Base):
    __tablename__ = "bugs"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    project_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    test_run_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), ForeignKey("test_runs.id", ondelete="SET NULL"))
    agent_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), ForeignKey("agents.id", ondelete="SET NULL"))
    test_case_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), ForeignKey("test_cases.id", ondelete="SET NULL"))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    severity: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, server_default="open")
    affected_url: Mapped[str | None] = mapped_column(Text)
    expected_result: Mapped[str | None] = mapped_column(Text)
    actual_result: Mapped[str | None] = mapped_column(Text)
    ai_summary: Mapped[str | None] = mapped_column(Text)
    suggested_fix: Mapped[str | None] = mapped_column(Text)
    ai_consensus_status: Mapped[str | None] = mapped_column(String(50))
    ai_confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    reasoning_session_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), ForeignKey("llm_reasoning_sessions.id", ondelete="SET NULL"))
    fingerprint: Mapped[str | None] = mapped_column(Text)
    assigned_to: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), ForeignKey("users.id"))
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.current_timestamp())
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.current_timestamp())


class BugArtifact(TimestampMixin, Base):
    __tablename__ = "bug_artifacts"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    bug_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("bugs.id", ondelete="CASCADE"), nullable=False)
    artifact_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(120))
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    label: Mapped[str | None] = mapped_column(String(120))


class ReplayStep(TimestampMixin, Base):
    __tablename__ = "replay_steps"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    bug_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("bugs.id", ondelete="CASCADE"), nullable=False)
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    selector: Mapped[str | None] = mapped_column(Text)
    selector_hint: Mapped[str | None] = mapped_column(Text)
    input_value: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(Text)
    expected_result: Mapped[str | None] = mapped_column(Text)


class BrowserLog(TimestampMixin, Base):
    __tablename__ = "browser_logs"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    test_run_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), ForeignKey("test_runs.id", ondelete="CASCADE"))
    agent_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"))
    bug_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), ForeignKey("bugs.id", ondelete="SET NULL"))
    log_level: Mapped[str | None] = mapped_column(String(30))
    message: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(Text)
    line_number: Mapped[int | None] = mapped_column(Integer)
    column_number: Mapped[int | None] = mapped_column(Integer)


class NetworkLog(TimestampMixin, Base):
    __tablename__ = "network_logs"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    test_run_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), ForeignKey("test_runs.id", ondelete="CASCADE"))
    agent_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"))
    bug_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), ForeignKey("bugs.id", ondelete="SET NULL"))
    request_url: Mapped[str] = mapped_column(Text, nullable=False)
    method: Mapped[str | None] = mapped_column(String(20))
    status_code: Mapped[int | None] = mapped_column(Integer)
    resource_type: Mapped[str | None] = mapped_column(String(50))
    failure_text: Mapped[str | None] = mapped_column(Text)
    duration_ms: Mapped[int | None] = mapped_column(Integer)


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    test_run_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("test_runs.id", ondelete="CASCADE"), nullable=False)
    report_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_path: Mapped[str | None] = mapped_column(Text)
    content: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    generated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.current_timestamp())
