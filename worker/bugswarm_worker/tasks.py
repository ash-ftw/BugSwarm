from __future__ import annotations

import asyncio

from celery.exceptions import SoftTimeLimitExceeded
from sqlalchemy import text

from bugswarm_worker.agents.explorer import run_explorer_agent
from bugswarm_worker.ai.bug_validation import validate_bug_with_council
from bugswarm_worker.db import db_connection, update_agent_status, update_test_run_status
from bugswarm_worker.events import publish_event
from bugswarm_worker.queue import celery_app
from bugswarm_worker.replay import replay_bug
from bugswarm_worker.retention import cleanup_retention


@celery_app.task(bind=True, name="bugswarm.run_agent", acks_late=True)
def run_agent(self, job: dict) -> None:
    try:
        asyncio.run(run_explorer_agent(job))
    except SoftTimeLimitExceeded as exc:
        _mark_agent_failed(job, "Agent exceeded the configured duration limit.")
        raise exc
    except Exception as exc:
        if not _agent_already_terminal(job):
            _mark_agent_failed(job, str(exc))
        raise


@celery_app.task(name="bugswarm.replay_bug", acks_late=True)
def run_replay(job: dict) -> dict:
    return asyncio.run(replay_bug(job))


@celery_app.task(name="bugswarm.validate_bug", acks_late=True)
def run_bug_validation(job: dict) -> dict:
    return asyncio.run(validate_bug_with_council(job))


@celery_app.task(name="bugswarm.cleanup_retention", acks_late=True)
def run_retention_cleanup(job: dict | None = None) -> dict:
    return cleanup_retention(job)


def _agent_already_terminal(job: dict) -> bool:
    agent_id = job.get("agent_id")
    if not agent_id:
        return False
    with db_connection() as connection:
        status = connection.execute(
            text("SELECT status FROM agents WHERE id = :agent_id"),
            {"agent_id": agent_id},
        ).scalar_one_or_none()
    return status in {"completed", "failed", "cancelled"}


def _mark_agent_failed(job: dict, message: str) -> None:
    test_run_id = job.get("test_run_id")
    agent_id = job.get("agent_id")
    agent_type = str(job.get("agent_type") or "explorer")
    if not test_run_id or not agent_id:
        return

    with db_connection() as connection:
        update_agent_status(connection, agent_id, "failed", error_message=message, completed=True)
        update_test_run_status(connection, test_run_id, "failed", completed=True)

    publish_event(
        test_run_id,
        "agent_failed",
        {"agent_id": agent_id, "agent_type": agent_type, "status": "failed", "message": message},
    )
    publish_event(
        test_run_id,
        "test_run_failed",
        {"test_run_id": test_run_id, "status": "failed", "message": message},
    )
