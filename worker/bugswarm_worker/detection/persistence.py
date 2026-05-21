from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy.engine import Connection

from bugswarm_worker.db import insert_bug_artifact, insert_replay_step, upsert_bug
from bugswarm_worker.detection.rules import DetectedBug
from bugswarm_worker.events import publish_event


def persist_detected_bug(
    connection: Connection,
    *,
    project_id: str,
    test_run_id: str,
    agent_id: str,
    bug: DetectedBug,
    screenshot_path: str | None = None,
    dom_snapshot_path: str | None = None,
    replay: list[dict[str, Any]] | None = None,
) -> tuple[str, bool]:
    bug_id, created = upsert_bug(
        connection,
        {
            "project_id": project_id,
            "test_run_id": test_run_id,
            "agent_id": agent_id,
            "test_case_id": None,
            "title": bug.title,
            "description": None,
            "category": bug.category,
            "severity": bug.severity,
            "affected_url": bug.affected_url,
            "expected_result": bug.expected_result,
            "actual_result": bug.actual_result,
            "ai_summary": None,
            "suggested_fix": None,
            "ai_consensus_status": None,
            "ai_confidence": None,
            "reasoning_session_id": None,
            "fingerprint": bug.fingerprint,
        },
    )
    if screenshot_path:
        _insert_artifact(connection, bug_id, "screenshot", screenshot_path, "image/png", "Failure screenshot")
    if dom_snapshot_path:
        _insert_artifact(connection, bug_id, "dom_snapshot", dom_snapshot_path, "text/html", "DOM snapshot")
    for index, step in enumerate(replay or [], start=1):
        insert_replay_step(
            connection,
            {
                "bug_id": bug_id,
                "step_order": index,
                "action_type": step.get("action_type") or "goto",
                "selector": step.get("selector"),
                "selector_hint": step.get("selector_hint"),
                "input_value": step.get("input_value"),
                "url": step.get("url") or bug.affected_url,
                "expected_result": bug.expected_result,
            },
        )
    if created:
        publish_event(
            test_run_id,
            "bug_found",
            {
                "bug_id": bug_id,
                "agent_id": agent_id,
                "severity": bug.severity,
                "category": bug.category,
                "title": bug.title,
                "url": bug.affected_url,
            },
        )
    return bug_id, created


def _insert_artifact(
    connection: Connection,
    bug_id: str,
    artifact_type: str,
    file_path: str,
    mime_type: str,
    label: str,
) -> None:
    path = Path(file_path)
    insert_bug_artifact(
        connection,
        {
            "bug_id": bug_id,
            "artifact_type": artifact_type,
            "file_path": file_path,
            "mime_type": mime_type,
            "file_size_bytes": path.stat().st_size if path.exists() else None,
            "label": label,
        },
    )
