from __future__ import annotations

import hashlib
import time
from pathlib import Path
from typing import Any

from playwright.async_api import async_playwright
from sqlalchemy import text

from bugswarm_worker.browser.extractor import extract_page
from bugswarm_worker.browser.scope import is_url_allowed, normalize_url
from bugswarm_worker.config import settings
from bugswarm_worker.db import (
    db_connection,
    insert_agent_step,
    insert_browser_log,
    insert_discovered_page,
    insert_network_log,
    is_test_run_cancelled,
    replace_page_elements,
    update_agent_status,
    update_test_run_status,
)


async def run_explorer_agent(job: dict[str, Any]) -> None:
    project_id = job["project_id"]
    test_run_id = job["test_run_id"]
    agent_id = job["agent_id"]
    base_url = job["base_url"]
    max_depth = int(job.get("max_depth", 3))
    max_duration_seconds = max(60, int(job.get("max_duration_minutes", 30)) * 60)
    viewport = job.get("viewport", {"width": 1440, "height": 900})
    allowed_patterns = job.get("allowed_patterns", [])
    excluded_patterns = job.get("excluded_patterns", [])

    deadline = time.monotonic() + max_duration_seconds
    step_order = 0
    queue: list[tuple[str, int]] = [(base_url, 0)]
    visited: set[str] = set()
    network_events: list[dict[str, Any]] = []
    console_events: list[dict[str, Any]] = []

    with db_connection() as connection:
        update_test_run_status(connection, test_run_id, "running")
        update_agent_status(connection, agent_id, "running", current_url=base_url)

    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": int(viewport["width"]), "height": int(viewport["height"])},
                ignore_https_errors=True,
            )
            page = await context.new_page()

            page.on("console", lambda message: console_events.append(_console_event(message)))
            page.on("requestfailed", lambda request: network_events.append(_request_failed_event(request)))
            page.on("response", lambda response: _record_failed_response(network_events, response))

            while queue and time.monotonic() < deadline:
                url, depth = queue.pop(0)
                normalized_url = normalize_url(base_url, url)
                if normalized_url in visited or depth > max_depth:
                    continue
                if not is_url_allowed(base_url, normalized_url, allowed_patterns, excluded_patterns):
                    continue

                with db_connection() as connection:
                    if is_test_run_cancelled(connection, test_run_id):
                        update_agent_status(connection, agent_id, "cancelled", completed=True)
                        await context.close()
                        await browser.close()
                        return
                    update_agent_status(connection, agent_id, "running", current_url=normalized_url)

                visited.add(normalized_url)
                step_order += 1
                started = time.perf_counter()
                status = "passed"
                error_message = None
                status_code = None
                content_hash = None
                url_before = page.url

                try:
                    response = await page.goto(normalized_url, wait_until="domcontentloaded", timeout=30_000)
                    status_code = response.status if response else None
                except Exception as exc:
                    status = "failed"
                    error_message = str(exc)

                if status == "passed":
                    try:
                        await page.wait_for_load_state("networkidle", timeout=5_000)
                    except Exception:
                        pass

                screenshot_path = await _capture_screenshot(page, test_run_id, agent_id, step_order)
                page_data = await extract_page(page)
                content = await page.content()
                content_hash = hashlib.sha256(content.encode("utf-8", errors="ignore")).hexdigest()
                duration_ms = int((time.perf_counter() - started) * 1000)

                discovered_page_id = None
                with db_connection() as connection:
                    insert_agent_step(
                        connection,
                        {
                            "agent_id": agent_id,
                            "step_order": step_order,
                            "action_type": "goto",
                            "target_selector": None,
                            "target_text": None,
                            "input_value": None,
                            "url_before": url_before,
                            "url_after": page.url,
                            "status": status,
                            "error_message": error_message,
                            "screenshot_artifact_id": None,
                            "dom_snapshot_artifact_id": None,
                            "duration_ms": duration_ms,
                        },
                    )
                    discovered_page_id = insert_discovered_page(
                        connection,
                        {
                            "project_id": project_id,
                            "test_run_id": test_run_id,
                            "url": page.url,
                            "title": page_data.get("title"),
                            "status_code": status_code,
                            "content_hash": content_hash,
                            "page_type": _classify_page(page_data),
                            "forms_count": len(page_data.get("forms", [])),
                            "links_count": len(page_data.get("links", [])),
                            "buttons_count": len(page_data.get("buttons", [])),
                            "discovered_by_agent_id": agent_id,
                        },
                    )
                    replace_page_elements(
                        connection,
                        discovered_page_id,
                        [
                            *page_data.get("forms", []),
                            *page_data.get("links", []),
                            *page_data.get("buttons", []),
                            *page_data.get("inputs", []),
                        ],
                    )
                    _flush_events(connection, test_run_id, agent_id, console_events, network_events)

                if status == "failed":
                    continue

                for link in page_data.get("links", []):
                    href = link.get("href")
                    if not href:
                        continue
                    next_url = normalize_url(page.url, href)
                    if next_url not in visited and is_url_allowed(base_url, next_url, allowed_patterns, excluded_patterns):
                        queue.append((next_url, depth + 1))

            await context.close()
            await browser.close()

        with db_connection() as connection:
            update_agent_status(connection, agent_id, "completed", completed=True)
            _complete_run_if_all_agents_finished(connection, test_run_id)
    except Exception as exc:
        with db_connection() as connection:
            update_agent_status(connection, agent_id, "failed", error_message=str(exc), completed=True)
            update_test_run_status(connection, test_run_id, "failed", completed=True)
        raise


async def _capture_screenshot(page, test_run_id: str, agent_id: str, step_order: int) -> str:
    screenshot_dir = Path(settings.artifact_storage_root) / "screenshots" / test_run_id / agent_id
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    screenshot_path = screenshot_dir / f"step-{step_order:04d}.png"
    await page.screenshot(path=str(screenshot_path), full_page=True)
    return str(screenshot_path)


def _console_event(message) -> dict[str, Any]:
    location = message.location
    return {
        "log_level": message.type,
        "message": message.text,
        "source_url": location.get("url") if location else None,
        "line_number": location.get("lineNumber") if location else None,
        "column_number": location.get("columnNumber") if location else None,
    }


def _request_failed_event(request) -> dict[str, Any]:
    failure = request.failure
    return {
        "request_url": request.url,
        "method": request.method,
        "status_code": None,
        "resource_type": request.resource_type,
        "failure_text": failure or "request failed",
        "duration_ms": None,
    }


def _record_failed_response(network_events: list[dict[str, Any]], response) -> None:
    if response.status < 400:
        return
    network_events.append(
        {
            "request_url": response.url,
            "method": response.request.method,
            "status_code": response.status,
            "resource_type": response.request.resource_type,
            "failure_text": response.status_text,
            "duration_ms": None,
        }
    )


def _flush_events(connection, test_run_id: str, agent_id: str, console_events: list[dict], network_events: list[dict]) -> None:
    while console_events:
        event = console_events.pop(0)
        if event.get("log_level") in {"error", "warning"}:
            insert_browser_log(connection, {"test_run_id": test_run_id, "agent_id": agent_id, **event})
    while network_events:
        insert_network_log(connection, {"test_run_id": test_run_id, "agent_id": agent_id, **network_events.pop(0)})


def _classify_page(page_data: dict[str, Any]) -> str:
    if page_data.get("forms"):
        return "form"
    if page_data.get("buttons"):
        return "interactive"
    return "content"


def _complete_run_if_all_agents_finished(connection, test_run_id: str) -> None:
    unfinished = connection.execute(
        text(
            """
        SELECT COUNT(*)
        FROM agents
        WHERE test_run_id = :test_run_id
          AND status NOT IN ('completed', 'failed', 'cancelled')
        """
        ),
        {"test_run_id": test_run_id},
    ).scalar_one()
    failed = connection.execute(
        text(
            """
        SELECT COUNT(*)
        FROM agents
        WHERE test_run_id = :test_run_id
          AND status = 'failed'
        """
        ),
        {"test_run_id": test_run_id},
    ).scalar_one()
    if unfinished == 0:
        update_test_run_status(connection, test_run_id, "failed" if failed else "completed", completed=True)
