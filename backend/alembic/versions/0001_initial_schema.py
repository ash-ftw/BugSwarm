"""Initial BugSwarm schema.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-05-19
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False, unique=True),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("role", sa.String(length=30), nullable=False, server_default="tester"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
    )

    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("base_url", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="active"),
        sa.Column("default_max_depth", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("default_agent_count", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("default_test_intensity", sa.String(length=30), nullable=False, server_default="medium"),
        sa.Column("llm_council_enabled", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
        sa.Column("llm_consensus_mode", sa.String(length=50), nullable=False, server_default="majority_vote"),
        sa.Column("free_ai_mode", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
    )

    op.create_table(
        "project_scopes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scope_type", sa.String(length=30), nullable=False),
        sa.Column("pattern", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
    )

    op.create_table(
        "auth_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("auth_type", sa.String(length=50), nullable=False),
        sa.Column("login_url", sa.Text()),
        sa.Column("username_selector", sa.Text()),
        sa.Column("password_selector", sa.Text()),
        sa.Column("submit_selector", sa.Text()),
        sa.Column("username_value", sa.Text()),
        sa.Column("encrypted_password_value", sa.Text()),
        sa.Column("storage_state_path", sa.Text()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
    )

    op.create_table(
        "test_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="queued"),
        sa.Column("agent_count", sa.Integer(), nullable=False),
        sa.Column("max_depth", sa.Integer(), nullable=False),
        sa.Column("max_duration_minutes", sa.Integer(), nullable=False),
        sa.Column("test_intensity", sa.String(length=30), nullable=False),
        sa.Column("started_at", sa.DateTime()),
        sa.Column("completed_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("summary", postgresql.JSONB()),
    )

    op.create_table(
        "llm_provider_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider_key", sa.String(length=30), nullable=False),
        sa.Column("model_name", sa.String(length=120), nullable=False),
        sa.Column("base_url", sa.Text()),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
        sa.Column("is_free_mode", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("max_retries", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("rate_limit_policy", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.UniqueConstraint("project_id", "provider_key"),
    )

    op.create_table(
        "agents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("test_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("test_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="queued"),
        sa.Column("browser", sa.String(length=50), nullable=False, server_default="chromium"),
        sa.Column("viewport_width", sa.Integer()),
        sa.Column("viewport_height", sa.Integer()),
        sa.Column("current_url", sa.Text()),
        sa.Column("started_at", sa.DateTime()),
        sa.Column("completed_at", sa.DateTime()),
        sa.Column("error_message", sa.Text()),
        sa.Column("metadata", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
    )

    op.create_table(
        "discovered_pages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("test_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("test_runs.id", ondelete="CASCADE")),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("title", sa.Text()),
        sa.Column("status_code", sa.Integer()),
        sa.Column("content_hash", sa.Text()),
        sa.Column("page_type", sa.String(length=80)),
        sa.Column("forms_count", sa.Integer(), server_default="0"),
        sa.Column("links_count", sa.Integer(), server_default="0"),
        sa.Column("buttons_count", sa.Integer(), server_default="0"),
        sa.Column("discovered_by_agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id")),
        sa.Column("first_seen_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column("last_seen_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
    )

    op.create_table(
        "test_cases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("test_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("test_runs.id", ondelete="SET NULL")),
        sa.Column("name", sa.String(length=220), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("source", sa.String(length=50), nullable=False, server_default="ai"),
        sa.Column("priority", sa.String(length=30), nullable=False, server_default="medium"),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="generated"),
        sa.Column("expected_result", sa.Text()),
        sa.Column("ai_prompt_hash", sa.Text()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
    )

    op.create_table(
        "llm_reasoning_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("test_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("test_runs.id", ondelete="CASCADE")),
        sa.Column("bug_id", postgresql.UUID(as_uuid=True)),
        sa.Column("task_type", sa.String(length=50), nullable=False),
        sa.Column("prompt_fingerprint", sa.String(length=128), nullable=False),
        sa.Column("consensus_status", sa.String(length=50), nullable=False),
        sa.Column("consensus_mode", sa.String(length=50), nullable=False, server_default="majority_vote"),
        sa.Column("final_rationale", sa.Text()),
        sa.Column("requires_human_review", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
        sa.Column("metadata", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
    )

    op.create_table(
        "llm_model_responses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("reasoning_session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("llm_reasoning_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider_key", sa.String(length=30), nullable=False),
        sa.Column("model_name", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="completed"),
        sa.Column("confidence", sa.Numeric(4, 3)),
        sa.Column("vote", sa.String(length=40)),
        sa.Column("rationale_summary", sa.Text()),
        sa.Column("output", postgresql.JSONB()),
        sa.Column("error_message", sa.Text()),
        sa.Column("latency_ms", sa.Integer()),
        sa.Column("token_usage", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
    )

    op.create_table(
        "agent_steps",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("step_order", sa.Integer(), nullable=False),
        sa.Column("action_type", sa.String(length=50), nullable=False),
        sa.Column("target_selector", sa.Text()),
        sa.Column("target_text", sa.Text()),
        sa.Column("input_value", sa.Text()),
        sa.Column("url_before", sa.Text()),
        sa.Column("url_after", sa.Text()),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("error_message", sa.Text()),
        sa.Column("screenshot_artifact_id", postgresql.UUID(as_uuid=True)),
        sa.Column("dom_snapshot_artifact_id", postgresql.UUID(as_uuid=True)),
        sa.Column("duration_ms", sa.Integer()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
    )

    op.create_table(
        "page_elements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("discovered_page_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("discovered_pages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("element_type", sa.String(length=50), nullable=False),
        sa.Column("selector", sa.Text()),
        sa.Column("role", sa.Text()),
        sa.Column("label", sa.Text()),
        sa.Column("placeholder", sa.Text()),
        sa.Column("text_content", sa.Text()),
        sa.Column("href", sa.Text()),
        sa.Column("is_visible", sa.Boolean()),
        sa.Column("is_enabled", sa.Boolean()),
        sa.Column("bounding_box", postgresql.JSONB()),
        sa.Column("metadata", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
    )

    op.create_table(
        "test_steps",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("test_case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("test_cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("step_order", sa.Integer(), nullable=False),
        sa.Column("action_type", sa.String(length=50), nullable=False),
        sa.Column("selector_hint", sa.Text()),
        sa.Column("selector_resolved", sa.Text()),
        sa.Column("input_value", sa.Text()),
        sa.Column("expected_observation", sa.Text()),
        sa.Column("timeout_ms", sa.Integer(), server_default="5000"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
    )

    op.create_table(
        "bugs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("test_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("test_runs.id", ondelete="SET NULL")),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id", ondelete="SET NULL")),
        sa.Column("test_case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("test_cases.id", ondelete="SET NULL")),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("severity", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="open"),
        sa.Column("affected_url", sa.Text()),
        sa.Column("expected_result", sa.Text()),
        sa.Column("actual_result", sa.Text()),
        sa.Column("ai_summary", sa.Text()),
        sa.Column("suggested_fix", sa.Text()),
        sa.Column("ai_consensus_status", sa.String(length=50)),
        sa.Column("ai_confidence", sa.Numeric(4, 3)),
        sa.Column("reasoning_session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("llm_reasoning_sessions.id", ondelete="SET NULL")),
        sa.Column("fingerprint", sa.Text()),
        sa.Column("assigned_to", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("first_seen_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column("last_seen_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
    )

    op.create_table(
        "bug_artifacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("bug_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("bugs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("artifact_type", sa.String(length=50), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("mime_type", sa.String(length=120)),
        sa.Column("file_size_bytes", sa.BigInteger()),
        sa.Column("label", sa.String(length=120)),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
    )

    op.create_table(
        "replay_steps",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("bug_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("bugs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("step_order", sa.Integer(), nullable=False),
        sa.Column("action_type", sa.String(length=50), nullable=False),
        sa.Column("selector", sa.Text()),
        sa.Column("selector_hint", sa.Text()),
        sa.Column("input_value", sa.Text()),
        sa.Column("url", sa.Text()),
        sa.Column("expected_result", sa.Text()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
    )

    op.create_table(
        "browser_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("test_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("test_runs.id", ondelete="CASCADE")),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id", ondelete="CASCADE")),
        sa.Column("bug_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("bugs.id", ondelete="SET NULL")),
        sa.Column("log_level", sa.String(length=30)),
        sa.Column("message", sa.Text()),
        sa.Column("source_url", sa.Text()),
        sa.Column("line_number", sa.Integer()),
        sa.Column("column_number", sa.Integer()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
    )

    op.create_table(
        "network_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("test_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("test_runs.id", ondelete="CASCADE")),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id", ondelete="CASCADE")),
        sa.Column("bug_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("bugs.id", ondelete="SET NULL")),
        sa.Column("request_url", sa.Text(), nullable=False),
        sa.Column("method", sa.String(length=20)),
        sa.Column("status_code", sa.Integer()),
        sa.Column("resource_type", sa.String(length=50)),
        sa.Column("failure_text", sa.Text()),
        sa.Column("duration_ms", sa.Integer()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
    )

    op.create_table(
        "reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("test_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("test_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("report_type", sa.String(length=50), nullable=False),
        sa.Column("file_path", sa.Text()),
        sa.Column("content", postgresql.JSONB()),
        sa.Column("generated_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
    )

    op.create_index("idx_projects_user_id", "projects", ["user_id"])
    op.create_index("idx_test_runs_project_id", "test_runs", ["project_id"])
    op.create_index("idx_agents_test_run_id", "agents", ["test_run_id"])
    op.create_index("idx_agent_steps_agent_id", "agent_steps", ["agent_id"])
    op.create_index("idx_bugs_project_id", "bugs", ["project_id"])
    op.create_index("idx_bugs_test_run_id", "bugs", ["test_run_id"])
    op.create_index("idx_bugs_severity", "bugs", ["severity"])
    op.create_index("idx_bugs_status", "bugs", ["status"])
    op.create_index("idx_discovered_pages_project_id", "discovered_pages", ["project_id"])
    op.create_index("idx_browser_logs_agent_id", "browser_logs", ["agent_id"])
    op.create_index("idx_network_logs_agent_id", "network_logs", ["agent_id"])
    op.create_index("idx_llm_provider_configs_project_id", "llm_provider_configs", ["project_id"])
    op.create_index("idx_llm_reasoning_sessions_test_run_id", "llm_reasoning_sessions", ["test_run_id"])
    op.create_index("idx_llm_model_responses_session_id", "llm_model_responses", ["reasoning_session_id"])


def downgrade() -> None:
    for table_name in (
        "reports",
        "network_logs",
        "browser_logs",
        "replay_steps",
        "bug_artifacts",
        "bugs",
        "test_steps",
        "page_elements",
        "agent_steps",
        "llm_model_responses",
        "llm_reasoning_sessions",
        "test_cases",
        "discovered_pages",
        "agents",
        "llm_provider_configs",
        "test_runs",
        "auth_profiles",
        "project_scopes",
        "projects",
        "users",
    ):
        op.drop_table(table_name)
