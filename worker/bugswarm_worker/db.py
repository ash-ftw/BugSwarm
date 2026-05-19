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
