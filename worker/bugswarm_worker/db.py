from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection

from bugswarm_worker.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)


@contextmanager
def db_connection() -> Iterator[Connection]:
    with engine.begin() as connection:
        yield connection


def as_jsonb(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True)


def update_test_run_status(connection: Connection, test_run_id: str, status: str, completed: bool = False) -> None:
    completed_clause = ", completed_at = CURRENT_TIMESTAMP" if completed else ""
    connection.execute(
        text(
            f"""
            UPDATE test_runs
            SET status = :status,
                started_at = COALESCE(started_at, CURRENT_TIMESTAMP)
                {completed_clause}
            WHERE id = :test_run_id
            """
        ),
        {"status": status, "test_run_id": test_run_id},
    )


def merge_test_run_summary(connection: Connection, test_run_id: str, summary_patch: dict[str, Any]) -> None:
    connection.execute(
        text(
            """
            UPDATE test_runs
            SET summary = COALESCE(summary, '{}'::jsonb) || CAST(:summary_patch AS jsonb)
            WHERE id = :test_run_id
            """
        ),
        {"test_run_id": test_run_id, "summary_patch": as_jsonb(summary_patch)},
    )


def update_agent_status(
    connection: Connection,
    agent_id: str,
    status: str,
    current_url: str | None = None,
    error_message: str | None = None,
    completed: bool = False,
) -> None:
    completed_clause = ", completed_at = CURRENT_TIMESTAMP" if completed else ""
    connection.execute(
        text(
            f"""
            UPDATE agents
            SET status = :status,
                current_url = COALESCE(:current_url, current_url),
                error_message = :error_message,
                started_at = COALESCE(started_at, CURRENT_TIMESTAMP)
                {completed_clause}
            WHERE id = :agent_id
            """
        ),
        {
            "agent_id": agent_id,
            "status": status,
            "current_url": current_url,
            "error_message": error_message,
        },
    )


def is_test_run_cancelled(connection: Connection, test_run_id: str) -> bool:
    status = connection.execute(
        text("SELECT status FROM test_runs WHERE id = :test_run_id"),
        {"test_run_id": test_run_id},
    ).scalar_one_or_none()
    return status == "cancelled"


def insert_agent_step(connection: Connection, values: dict[str, Any]) -> str:
    return str(
        connection.execute(
            text(
                """
                INSERT INTO agent_steps (
                    agent_id, step_order, action_type, target_selector, target_text,
                    input_value, url_before, url_after, status, error_message,
                    screenshot_artifact_id, dom_snapshot_artifact_id, duration_ms
                )
                VALUES (
                    :agent_id, :step_order, :action_type, :target_selector, :target_text,
                    :input_value, :url_before, :url_after, :status, :error_message,
                    :screenshot_artifact_id, :dom_snapshot_artifact_id, :duration_ms
                )
                RETURNING id
                """
            ),
            values,
        ).scalar_one()
    )


def insert_discovered_page(connection: Connection, values: dict[str, Any]) -> str:
    existing = connection.execute(
        text(
            """
            SELECT id FROM discovered_pages
            WHERE test_run_id = :test_run_id AND url = :url
            LIMIT 1
            """
        ),
        {"test_run_id": values["test_run_id"], "url": values["url"]},
    ).scalar_one_or_none()
    if existing:
        connection.execute(
            text(
                """
                UPDATE discovered_pages
                SET title = :title,
                    status_code = :status_code,
                    content_hash = :content_hash,
                    page_type = :page_type,
                    forms_count = :forms_count,
                    links_count = :links_count,
                    buttons_count = :buttons_count,
                    discovered_by_agent_id = :discovered_by_agent_id,
                    last_seen_at = CURRENT_TIMESTAMP
                WHERE id = :id
                """
            ),
            {**values, "id": existing},
        )
        return str(existing)

    return str(
        connection.execute(
            text(
                """
                INSERT INTO discovered_pages (
                    project_id, test_run_id, url, title, status_code, content_hash,
                    page_type, forms_count, links_count, buttons_count, discovered_by_agent_id
                )
                VALUES (
                    :project_id, :test_run_id, :url, :title, :status_code, :content_hash,
                    :page_type, :forms_count, :links_count, :buttons_count, :discovered_by_agent_id
                )
                RETURNING id
                """
            ),
            values,
        ).scalar_one()
    )


def replace_page_elements(connection: Connection, discovered_page_id: str, elements: list[dict[str, Any]]) -> None:
    connection.execute(
        text("DELETE FROM page_elements WHERE discovered_page_id = :discovered_page_id"),
        {"discovered_page_id": discovered_page_id},
    )
    for element in elements:
        connection.execute(
            text(
                """
                INSERT INTO page_elements (
                    discovered_page_id, element_type, selector, role, label, placeholder,
                    text_content, href, is_visible, is_enabled, bounding_box, metadata
                )
                VALUES (
                    :discovered_page_id, :element_type, :selector, :role, :label, :placeholder,
                    :text_content, :href, :is_visible, :is_enabled,
                    CAST(:bounding_box AS jsonb), CAST(:metadata AS jsonb)
                )
                """
            ),
            {
                "discovered_page_id": discovered_page_id,
                "element_type": element.get("element_type"),
                "selector": element.get("selector"),
                "role": element.get("role"),
                "label": element.get("label"),
                "placeholder": element.get("placeholder"),
                "text_content": element.get("text_content"),
                "href": element.get("href"),
                "is_visible": element.get("is_visible"),
                "is_enabled": element.get("is_enabled"),
                "bounding_box": as_jsonb(element.get("bounding_box")),
                "metadata": as_jsonb(element.get("metadata", {})),
            },
        )


def insert_browser_log(connection: Connection, values: dict[str, Any]) -> None:
    connection.execute(
        text(
            """
            INSERT INTO browser_logs (
                test_run_id, agent_id, bug_id, log_level, message, source_url,
                line_number, column_number
            )
            VALUES (
                :test_run_id, :agent_id, NULL, :log_level, :message, :source_url,
                :line_number, :column_number
            )
            """
        ),
        values,
    )


def insert_network_log(connection: Connection, values: dict[str, Any]) -> None:
    connection.execute(
        text(
            """
            INSERT INTO network_logs (
                test_run_id, agent_id, bug_id, request_url, method, status_code,
                resource_type, failure_text, duration_ms
            )
            VALUES (
                :test_run_id, :agent_id, NULL, :request_url, :method, :status_code,
                :resource_type, :failure_text, :duration_ms
            )
            """
        ),
        values,
    )


def upsert_bug(connection: Connection, values: dict[str, Any]) -> tuple[str, bool]:
    existing = connection.execute(
        text(
            """
            SELECT id
            FROM bugs
            WHERE project_id = :project_id
              AND fingerprint = :fingerprint
            LIMIT 1
            """
        ),
        {"project_id": values["project_id"], "fingerprint": values.get("fingerprint")},
    ).scalar_one_or_none()
    if existing:
        connection.execute(
            text(
                """
                UPDATE bugs
                SET last_seen_at = CURRENT_TIMESTAMP,
                    test_run_id = COALESCE(:test_run_id, test_run_id),
                    agent_id = COALESCE(:agent_id, agent_id),
                    actual_result = :actual_result
                WHERE id = :id
                """
            ),
            {**values, "id": existing},
        )
        return str(existing), False

    bug_id = connection.execute(
        text(
            """
            INSERT INTO bugs (
                project_id, test_run_id, agent_id, test_case_id, title,
                description, category, severity, status, affected_url,
                expected_result, actual_result, ai_summary, suggested_fix,
                ai_consensus_status, ai_confidence, reasoning_session_id,
                fingerprint
            )
            VALUES (
                :project_id, :test_run_id, :agent_id, :test_case_id, :title,
                :description, :category, :severity, 'open', :affected_url,
                :expected_result, :actual_result, :ai_summary, :suggested_fix,
                :ai_consensus_status, :ai_confidence, :reasoning_session_id,
                :fingerprint
            )
            RETURNING id
            """
        ),
        values,
    ).scalar_one()
    return str(bug_id), True


def insert_bug_artifact(connection: Connection, values: dict[str, Any]) -> str:
    existing = connection.execute(
        text(
            """
            SELECT id
            FROM bug_artifacts
            WHERE bug_id = :bug_id
              AND artifact_type = :artifact_type
              AND file_path = :file_path
            LIMIT 1
            """
        ),
        values,
    ).scalar_one_or_none()
    if existing:
        return str(existing)
    return str(
        connection.execute(
            text(
                """
                INSERT INTO bug_artifacts (
                    bug_id, artifact_type, file_path, mime_type, file_size_bytes, label
                )
                VALUES (
                    :bug_id, :artifact_type, :file_path, :mime_type, :file_size_bytes, :label
                )
                RETURNING id
                """
            ),
            values,
        ).scalar_one()
    )


def insert_replay_step(connection: Connection, values: dict[str, Any]) -> str:
    existing = connection.execute(
        text(
            """
            SELECT id
            FROM replay_steps
            WHERE bug_id = :bug_id
              AND step_order = :step_order
            LIMIT 1
            """
        ),
        values,
    ).scalar_one_or_none()
    if existing:
        return str(existing)
    return str(
        connection.execute(
            text(
                """
                INSERT INTO replay_steps (
                    bug_id, step_order, action_type, selector, selector_hint,
                    input_value, url, expected_result
                )
                VALUES (
                    :bug_id, :step_order, :action_type, :selector, :selector_hint,
                    :input_value, :url, :expected_result
                )
                RETURNING id
                """
            ),
            values,
        ).scalar_one()
    )


def fetch_provider_configs(connection: Connection, project_id: str, provider_keys: list[str]) -> list[dict[str, Any]]:
    if not provider_keys:
        return []
    rows = connection.execute(
        text(
            """
            SELECT provider_key, model_name, base_url, is_enabled, timeout_seconds, max_retries
            FROM llm_provider_configs
            WHERE project_id = :project_id
              AND provider_key = ANY(:provider_keys)
            ORDER BY provider_key ASC
            """
        ),
        {"project_id": project_id, "provider_keys": provider_keys},
    ).mappings()
    return [dict(row) for row in rows]


def test_case_exists(connection: Connection, test_run_id: str, ai_prompt_hash: str) -> bool:
    return bool(
        connection.execute(
            text(
                """
                SELECT 1
                FROM test_cases
                WHERE test_run_id = :test_run_id
                  AND ai_prompt_hash = :ai_prompt_hash
                LIMIT 1
                """
            ),
            {"test_run_id": test_run_id, "ai_prompt_hash": ai_prompt_hash},
        ).scalar_one_or_none()
    )


def insert_reasoning_session(connection: Connection, values: dict[str, Any]) -> str:
    return str(
        connection.execute(
            text(
                """
                INSERT INTO llm_reasoning_sessions (
                    test_run_id, bug_id, task_type, prompt_fingerprint,
                    consensus_status, consensus_mode, final_rationale,
                    requires_human_review, metadata
                )
                VALUES (
                    :test_run_id, :bug_id, :task_type, :prompt_fingerprint,
                    :consensus_status, :consensus_mode, :final_rationale,
                    :requires_human_review, CAST(:metadata AS jsonb)
                )
                RETURNING id
                """
            ),
            {**values, "bug_id": values.get("bug_id"), "metadata": as_jsonb(values.get("metadata", {}))},
        ).scalar_one()
    )


def insert_model_response(connection: Connection, values: dict[str, Any]) -> str:
    return str(
        connection.execute(
            text(
                """
                INSERT INTO llm_model_responses (
                    reasoning_session_id, provider_key, model_name, status,
                    confidence, vote, rationale_summary, output,
                    error_message, latency_ms, token_usage
                )
                VALUES (
                    :reasoning_session_id, :provider_key, :model_name, :status,
                    :confidence, :vote, :rationale_summary, CAST(:output AS jsonb),
                    :error_message, :latency_ms, CAST(:token_usage AS jsonb)
                )
                RETURNING id
                """
            ),
            {
                **values,
                "output": as_jsonb(values.get("output", {})),
                "token_usage": as_jsonb(values.get("token_usage", {})),
            },
        ).scalar_one()
    )


def insert_test_case(connection: Connection, values: dict[str, Any]) -> str:
    return str(
        connection.execute(
            text(
                """
                INSERT INTO test_cases (
                    project_id, test_run_id, name, description, source, priority,
                    status, expected_result, ai_prompt_hash
                )
                VALUES (
                    :project_id, :test_run_id, :name, :description, :source, :priority,
                    :status, :expected_result, :ai_prompt_hash
                )
                RETURNING id
                """
            ),
            values,
        ).scalar_one()
    )


def insert_test_step(connection: Connection, values: dict[str, Any]) -> str:
    return str(
        connection.execute(
            text(
                """
                INSERT INTO test_steps (
                    test_case_id, step_order, action_type, selector_hint,
                    selector_resolved, input_value, expected_observation, timeout_ms
                )
                VALUES (
                    :test_case_id, :step_order, :action_type, :selector_hint,
                    :selector_resolved, :input_value, :expected_observation, :timeout_ms
                )
                RETURNING id
                """
            ),
            values,
        ).scalar_one()
    )


def update_test_case_status(connection: Connection, test_case_id: str, status: str) -> None:
    connection.execute(
        text("UPDATE test_cases SET status = :status WHERE id = :test_case_id"),
        {"test_case_id": test_case_id, "status": status},
    )


def fetch_bug_with_replay(connection: Connection, bug_id: str) -> dict[str, Any] | None:
    bug = connection.execute(
        text(
            """
            SELECT bugs.*, projects.base_url
            FROM bugs
            JOIN projects ON projects.id = bugs.project_id
            WHERE bugs.id = :bug_id
            """
        ),
        {"bug_id": bug_id},
    ).mappings().first()
    if bug is None:
        return None
    replay_steps = connection.execute(
        text(
            """
            SELECT *
            FROM replay_steps
            WHERE bug_id = :bug_id
            ORDER BY step_order ASC
            """
        ),
        {"bug_id": bug_id},
    ).mappings()
    artifacts = connection.execute(
        text(
            """
            SELECT *
            FROM bug_artifacts
            WHERE bug_id = :bug_id
            ORDER BY created_at ASC
            """
        ),
        {"bug_id": bug_id},
    ).mappings()
    return {
        **dict(bug),
        "replay_steps": [dict(row) for row in replay_steps],
        "artifacts": [dict(row) for row in artifacts],
    }


def fetch_bug_validation_evidence(connection: Connection, bug_id: str) -> dict[str, Any] | None:
    bug = fetch_bug_with_replay(connection, bug_id)
    if bug is None:
        return None
    browser_logs = connection.execute(
        text(
            """
            SELECT log_level, message, source_url, line_number, column_number, created_at
            FROM browser_logs
            WHERE test_run_id = :test_run_id
              AND (:affected_url IS NULL OR source_url = :affected_url)
            ORDER BY created_at DESC
            LIMIT 12
            """
        ),
        {"test_run_id": bug.get("test_run_id"), "affected_url": bug.get("affected_url")},
    ).mappings()
    network_logs = connection.execute(
        text(
            """
            SELECT request_url, method, status_code, resource_type, failure_text, duration_ms, created_at
            FROM network_logs
            WHERE test_run_id = :test_run_id
              AND (:affected_url IS NULL OR request_url = :affected_url)
            ORDER BY created_at DESC
            LIMIT 12
            """
        ),
        {"test_run_id": bug.get("test_run_id"), "affected_url": bug.get("affected_url")},
    ).mappings()
    return {
        **bug,
        "browser_logs": [dict(row) for row in browser_logs],
        "network_logs": [dict(row) for row in network_logs],
    }


def update_bug_ai_validation(connection: Connection, bug_id: str, values: dict[str, Any]) -> None:
    connection.execute(
        text(
            """
            UPDATE bugs
            SET severity = COALESCE(:severity, severity),
                ai_summary = COALESCE(:ai_summary, ai_summary),
                suggested_fix = COALESCE(:suggested_fix, suggested_fix),
                ai_consensus_status = :ai_consensus_status,
                ai_confidence = :ai_confidence,
                reasoning_session_id = :reasoning_session_id,
                last_seen_at = CURRENT_TIMESTAMP
            WHERE id = :bug_id
            """
        ),
        {
            "bug_id": bug_id,
            "severity": values.get("severity"),
            "ai_summary": values.get("ai_summary"),
            "suggested_fix": values.get("suggested_fix"),
            "ai_consensus_status": values.get("ai_consensus_status"),
            "ai_confidence": values.get("ai_confidence"),
            "reasoning_session_id": values.get("reasoning_session_id"),
        },
    )


def insert_report(connection: Connection, values: dict[str, Any]) -> str:
    return str(
        connection.execute(
            text(
                """
                INSERT INTO reports (test_run_id, report_type, file_path, content)
                VALUES (:test_run_id, :report_type, :file_path, CAST(:content AS jsonb))
                RETURNING id
                """
            ),
            {**values, "content": as_jsonb(values.get("content", {}))},
        ).scalar_one()
    )
