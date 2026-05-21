from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import text

from bugswarm_worker.config import settings
from bugswarm_worker.db import db_connection


def cleanup_retention(job: dict[str, Any] | None = None) -> dict[str, Any]:
    job = job or {}
    dry_run = bool(job.get("dry_run", False))
    policy = _policy_from_job(job)

    root = Path(settings.artifact_storage_root).resolve()
    result: dict[str, Any] = {
        "dry_run": dry_run,
        "storage_root": str(root),
        "policy": policy,
        "files": {},
        "database": {},
    }

    result["files"]["screenshots"] = _prune_directory(root, "screenshots", policy["screenshot_days"], dry_run)
    result["files"]["traces"] = _prune_directory(root, "traces", policy["trace_days"], dry_run)
    result["files"]["reports"] = _prune_directory(root, "reports", policy["report_days"], dry_run)
    result["database"] = _prune_database(policy, dry_run)
    return result


def _policy_from_job(job: dict[str, Any]) -> dict[str, int]:
    return {
        "screenshot_days": _positive_int(job.get("screenshot_days"), settings.screenshot_retention_days),
        "trace_days": _positive_int(job.get("trace_days"), settings.trace_retention_days),
        "report_days": _positive_int(job.get("report_days"), settings.report_retention_days),
        "browser_log_days": _positive_int(job.get("browser_log_days"), settings.browser_log_retention_days),
        "network_log_days": _positive_int(job.get("network_log_days"), settings.network_log_retention_days),
    }


def _positive_int(value: Any, fallback: int) -> int:
    try:
        parsed = int(value) if value is not None else int(fallback)
    except (TypeError, ValueError):
        return int(fallback)
    return max(parsed, 1)


def _prune_directory(root: Path, name: str, days: int, dry_run: bool) -> dict[str, Any]:
    target = (root / name).resolve()
    if target != root and root not in target.parents:
        raise ValueError(f"Refusing to prune path outside storage root: {target}")
    if not target.exists():
        return {"cutoff": _cutoff(days).isoformat(), "deleted": 0, "bytes": 0, "missing": True}

    cutoff = _cutoff(days)
    deleted = 0
    bytes_deleted = 0
    for path in target.rglob("*"):
        if not path.is_file() or path.name == ".gitkeep":
            continue
        modified_at = datetime.utcfromtimestamp(path.stat().st_mtime)
        if modified_at >= cutoff:
            continue
        deleted += 1
        bytes_deleted += path.stat().st_size
        if not dry_run:
            path.unlink()

    if not dry_run:
        _remove_empty_dirs(target)

    return {"cutoff": cutoff.isoformat(), "deleted": deleted, "bytes": bytes_deleted, "missing": False}


def _remove_empty_dirs(target: Path) -> None:
    for path in sorted((item for item in target.rglob("*") if item.is_dir()), key=lambda item: len(item.parts), reverse=True):
        try:
            path.rmdir()
        except OSError:
            continue


def _prune_database(policy: dict[str, int], dry_run: bool) -> dict[str, int]:
    browser_cutoff = _cutoff(policy["browser_log_days"])
    network_cutoff = _cutoff(policy["network_log_days"])
    screenshot_cutoff = _cutoff(policy["screenshot_days"])
    trace_cutoff = _cutoff(policy["trace_days"])
    report_cutoff = _cutoff(policy["report_days"])

    statements = {
        "browser_logs": (
            "DELETE FROM browser_logs WHERE created_at < :cutoff",
            {"cutoff": browser_cutoff},
        ),
        "network_logs": (
            "DELETE FROM network_logs WHERE created_at < :cutoff",
            {"cutoff": network_cutoff},
        ),
        "screenshot_artifacts": (
            """
            DELETE FROM bug_artifacts
            WHERE artifact_type IN ('screenshot', 'replay_screenshot')
              AND created_at < :cutoff
            """,
            {"cutoff": screenshot_cutoff},
        ),
        "dom_snapshot_artifacts": (
            "DELETE FROM bug_artifacts WHERE artifact_type = 'dom_snapshot' AND created_at < :cutoff",
            {"cutoff": trace_cutoff},
        ),
        "reports": (
            "DELETE FROM reports WHERE generated_at < :cutoff",
            {"cutoff": report_cutoff},
        ),
    }

    result: dict[str, int] = {}
    with db_connection() as connection:
        for name, (sql, params) in statements.items():
            if dry_run:
                count_sql = _delete_to_count_sql(sql)
                result[name] = int(connection.execute(text(count_sql), params).scalar_one() or 0)
            else:
                response = connection.execute(text(sql), params)
                result[name] = int(response.rowcount or 0)
    return result


def _delete_to_count_sql(sql: str) -> str:
    upper = " ".join(sql.strip().split())
    return upper.replace("DELETE FROM", "SELECT count(*) FROM", 1)


def _cutoff(days: int) -> datetime:
    return datetime.utcnow() - timedelta(days=days)
