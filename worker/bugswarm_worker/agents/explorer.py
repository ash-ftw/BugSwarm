from __future__ import annotations

import hashlib
import time
from pathlib import Path
from typing import Any

from playwright.async_api import async_playwright
from sqlalchemy import text

from bugswarm_worker.ai.generation import generate_and_execute_tests_for_page, page_supports_ai_generation
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
    merge_test_run_summary,
    replace_page_elements,
    update_agent_status,
    update_test_run_status,
)
from bugswarm_worker.detection.persistence import persist_detected_bug
from bugswarm_worker.detection.rules import (
    detect_blank_page,
    detect_console_error,
    detect_http_error,
    detect_infinite_loading,
    detect_navigation_failure,
    detect_network_failure,
    detect_page_crash,
)
from bugswarm_worker.events import publish_event

FORM_TERMS = ("login", "signup", "sign-up", "register", "contact", "checkout", "account", "profile", "search", "form")
NAVIGATION_TERMS = ("home", "about", "product", "pricing", "docs", "dashboard", "cart", "shop", "menu", "category")


async def run_explorer_agent(job: dict[str, Any]) -> None:
    project_id = job["project_id"]
    test_run_id = job["test_run_id"]
    agent_id = job["agent_id"]
    base_url = job["base_url"]
    agent_type = str(job.get("agent_type") or "explorer")
    max_depth = int(job.get("max_depth", 3))
    max_actions = int(job.get("max_actions", _default_action_limit(agent_type)))
    max_duration_seconds = max(60, int(job.get("max_duration_minutes", 30)) * 60)
    viewport = job.get("viewport", {"width": 1440, "height": 900})
    allowed_patterns = job.get("allowed_patterns", [])
    excluded_patterns = job.get("excluded_patterns", [])
    safe_mode = bool(job.get("safe_mode", True))
    llm_council_enabled = bool(job.get("llm_council_enabled", True))
    llm_providers = [str(provider) for provider in job.get("llm_providers", ["groq", "gptoss", "gemini"])]
    llm_consensus_mode = str(job.get("llm_consensus_mode") or "majority_vote")
    auth_profile = job.get("auth_profile") if isinstance(job.get("auth_profile"), dict) else None

    deadline = time.monotonic() + max_duration_seconds
    step_order = 0
    end_reason = "completed"
    ai_pages_processed = 0
    max_ai_pages = _ai_page_limit(agent_type)
    queue: list[tuple[str, int]] = [(base_url, 0)]
    queued: set[str] = {normalize_url(base_url, base_url)}
    visited: set[str] = set()
    network_events: list[dict[str, Any]] = []
    console_events: list[dict[str, Any]] = []
    page_crashes: list[str] = []

    with db_connection() as connection:
        update_test_run_status(connection, test_run_id, "running")
        update_agent_status(connection, agent_id, "starting", current_url=base_url)

    publish_event(
        test_run_id,
        "agent_started",
        {
            "agent_id": agent_id,
            "agent_type": agent_type,
            "status": "starting",
            "message": f"{agent_type.title()} Agent started",
        },
    )

    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            context_options: dict[str, Any] = {
                "viewport": {"width": int(viewport["width"]), "height": int(viewport["height"])},
                "ignore_https_errors": True,
            }
            storage_state_path = str(auth_profile.get("storage_state_path") or "") if auth_profile else ""
            if storage_state_path and Path(storage_state_path).exists():
                context_options["storage_state"] = storage_state_path
            context = await browser.new_context(**context_options)
            page = await context.new_page()

            with db_connection() as connection:
                update_agent_status(connection, agent_id, "running", current_url=base_url)
            publish_event(
                test_run_id,
                "agent_running",
                {"agent_id": agent_id, "agent_type": agent_type, "status": "running", "current_url": base_url},
            )

            page.on("console", lambda message: console_events.append(_console_event(message)))
            page.on("requestfailed", lambda request: network_events.append(_request_failed_event(request)))
            page.on("response", lambda response: _record_failed_response(network_events, response))
            page.on("crash", lambda: page_crashes.append(page.url or base_url))
            step_order = await _apply_auth_profile(
                context=context,
                page=page,
                auth_profile=auth_profile,
                base_url=base_url,
                test_run_id=test_run_id,
                agent_id=agent_id,
                agent_type=agent_type,
                step_order=step_order,
                deadline=deadline,
            )

            try:
                while queue and time.monotonic() < deadline and step_order < max_actions:
                    url, depth = queue.pop(0)
                    normalized_url = normalize_url(base_url, url)
                    if normalized_url in visited or depth > max_depth:
                        continue
                    if not is_url_allowed(base_url, normalized_url, allowed_patterns, excluded_patterns):
                        continue

                    with db_connection() as connection:
                        if is_test_run_cancelled(connection, test_run_id):
                            update_agent_status(connection, agent_id, "cancelled", completed=True)
                            _complete_run_if_all_agents_finished(connection, test_run_id)
                            publish_event(
                                test_run_id,
                                "agent_cancelled",
                                {"agent_id": agent_id, "agent_type": agent_type},
                            )
                            return
                        update_agent_status(connection, agent_id, "running", current_url=normalized_url)

                    visited.add(normalized_url)
                    step_order += 1
                    started = time.perf_counter()
                    status = "passed"
                    error_message = None
                    status_code = None
                    network_idle_timed_out = False
                    url_before = page.url

                    try:
                        response = await page.goto(
                            normalized_url,
                            wait_until="domcontentloaded",
                            timeout=_remaining_timeout_ms(deadline, 30_000),
                        )
                        status_code = response.status if response else None
                    except Exception as exc:
                        status = "failed"
                        error_message = str(exc)

                    if status == "passed":
                        try:
                            await page.wait_for_load_state("networkidle", timeout=_remaining_timeout_ms(deadline, 5_000))
                        except Exception:
                            network_idle_timed_out = True

                    screenshot_path = await _capture_screenshot(page, test_run_id, agent_id, step_order)
                    page_data = await extract_page(page)
                    content = await page.content()
                    dom_snapshot_path = _write_dom_snapshot(content, test_run_id, agent_id, step_order)
                    content_hash = hashlib.sha256(content.encode("utf-8", errors="ignore")).hexdigest()
                    duration_ms = int((time.perf_counter() - started) * 1000)

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
                        _detect_and_store_page_bugs(
                            connection,
                            project_id,
                            test_run_id,
                            agent_id,
                            page.url,
                            status,
                            error_message,
                            status_code,
                            page_data,
                            network_idle_timed_out,
                            page_crashes,
                            screenshot_path,
                            dom_snapshot_path,
                        )
                        _flush_events(connection, project_id, test_run_id, agent_id, page.url, console_events, network_events)
                        _publish_progress(
                            connection,
                            test_run_id,
                            agent_id,
                            agent_type,
                            step_order,
                            max_actions,
                            len(visited),
                            len(queue),
                            page.url,
                        )

                    publish_event(
                        test_run_id,
                        "step_completed",
                        {
                            "agent_id": agent_id,
                            "agent_type": agent_type,
                            "url": page.url,
                            "action": "goto",
                            "status": status,
                            "screenshot_path": screenshot_path,
                        },
                    )
                    publish_event(
                        test_run_id,
                        "page_discovered",
                        {
                            "agent_id": agent_id,
                            "agent_type": agent_type,
                            "url": page.url,
                            "title": page_data.get("title"),
                            "forms_count": len(page_data.get("forms", [])),
                            "links_count": len(page_data.get("links", [])),
                        },
                    )

                    if agent_type == "form":
                        step_order = _record_form_steps(
                            test_run_id,
                            agent_id,
                            agent_type,
                            page.url,
                            page_data,
                            step_order,
                            max_actions,
                            safe_mode,
                        )
                    elif agent_type == "chaos":
                        step_order = _record_button_steps(
                            test_run_id,
                            agent_id,
                            agent_type,
                            page.url,
                            page_data,
                            step_order,
                            max_actions,
                            safe_mode,
                        )

                    if (
                        llm_council_enabled
                        and ai_pages_processed < max_ai_pages
                        and page_supports_ai_generation(page_data)
                        and time.monotonic() < deadline
                    ):
                        ai_result = await generate_and_execute_tests_for_page(
                            page=page,
                            project_id=project_id,
                            test_run_id=test_run_id,
                            agent_id=agent_id,
                            base_url=base_url,
                            page_data=page_data,
                            provider_keys=llm_providers,
                            consensus_mode=llm_consensus_mode,
                            safe_mode=safe_mode,
                            allowed_patterns=allowed_patterns,
                            excluded_patterns=excluded_patterns,
                            step_order=step_order,
                            deadline=deadline,
                        )
                        if ai_result.test_cases_created:
                            ai_pages_processed += 1
                            step_order += ai_result.agent_steps_created

                    if status == "failed":
                        continue

                    for next_url in _candidate_urls(agent_type, page.url, page_data):
                        if step_order >= max_actions:
                            break
                        if next_url in visited or next_url in queued:
                            continue
                        if is_url_allowed(base_url, next_url, allowed_patterns, excluded_patterns):
                            queued.add(next_url)
                            queue.append((next_url, depth + 1))
                if time.monotonic() >= deadline:
                    end_reason = "duration_limit"
                elif step_order >= max_actions:
                    end_reason = "action_limit"
                elif not queue:
                    end_reason = "queue_exhausted"
            finally:
                await context.close()
                await browser.close()

        with db_connection() as connection:
            update_agent_status(connection, agent_id, "reporting")
            publish_event(
                test_run_id,
                "agent_reporting",
                {"agent_id": agent_id, "agent_type": agent_type, "status": "reporting", "end_reason": end_reason},
            )
            update_agent_status(connection, agent_id, "completed", completed=True)
            publish_event(
                test_run_id,
                "agent_completed",
                {
                    "agent_id": agent_id,
                    "agent_type": agent_type,
                    "status": "completed",
                    "visited_count": len(visited),
                    "steps_completed": step_order,
                    "end_reason": end_reason,
                },
            )
            _complete_run_if_all_agents_finished(connection, test_run_id)
    except Exception as exc:
        with db_connection() as connection:
            update_agent_status(connection, agent_id, "failed", error_message=str(exc), completed=True)
            update_test_run_status(connection, test_run_id, "failed", completed=True)
            publish_event(
                test_run_id,
                "agent_failed",
                {"agent_id": agent_id, "agent_type": agent_type, "message": str(exc)},
            )
            publish_event(
                test_run_id,
                "test_run_failed",
                {"test_run_id": test_run_id, "message": str(exc)},
            )
        raise


async def _capture_screenshot(page, test_run_id: str, agent_id: str, step_order: int) -> str:
    screenshot_dir = Path(settings.artifact_storage_root) / "screenshots" / test_run_id / agent_id
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    screenshot_path = screenshot_dir / f"step-{step_order:04d}.png"
    await page.screenshot(path=str(screenshot_path), full_page=True)
    return str(screenshot_path)


def _write_dom_snapshot(content: str, test_run_id: str, agent_id: str, step_order: int) -> str:
    snapshot_dir = Path(settings.artifact_storage_root) / "traces" / test_run_id / agent_id
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path = snapshot_dir / f"step-{step_order:04d}.html"
    snapshot_path.write_text(content, encoding="utf-8")
    return str(snapshot_path)


async def _apply_auth_profile(
    *,
    context,
    page,
    auth_profile: dict[str, Any] | None,
    base_url: str,
    test_run_id: str,
    agent_id: str,
    agent_type: str,
    step_order: int,
    deadline: float,
) -> int:
    if not auth_profile or not auth_profile.get("is_active", True):
        return step_order

    step_order += 1
    auth_type = str(auth_profile.get("auth_type") or "form")
    profile_name = str(auth_profile.get("name") or "Auth profile")
    login_url = str(auth_profile.get("login_url") or base_url)
    status = "passed"
    error_message = None
    url_before = page.url
    started = time.perf_counter()

    publish_event(
        test_run_id,
        "auth_started",
        {"agent_id": agent_id, "agent_type": agent_type, "auth_profile": profile_name, "auth_type": auth_type},
    )

    try:
        if auth_type == "storage_state":
            storage_state_path = str(auth_profile.get("storage_state_path") or "")
            if not storage_state_path or not Path(storage_state_path).exists():
                raise ValueError("Configured storage state file was not found.")
        else:
            username_selector = str(auth_profile.get("username_selector") or "")
            password_selector = str(auth_profile.get("password_selector") or "")
            submit_selector = str(auth_profile.get("submit_selector") or "")
            if not username_selector or not password_selector:
                raise ValueError("Form auth requires username and password selectors.")

            await page.goto(login_url, wait_until="domcontentloaded", timeout=_remaining_timeout_ms(deadline, 30_000))
            await page.fill(username_selector, str(auth_profile.get("username_value") or ""), timeout=_remaining_timeout_ms(deadline, 10_000))
            await page.fill(password_selector, str(auth_profile.get("password_value") or ""), timeout=_remaining_timeout_ms(deadline, 10_000))
            if submit_selector:
                await page.click(submit_selector, timeout=_remaining_timeout_ms(deadline, 10_000))
            else:
                await page.press(password_selector, "Enter", timeout=_remaining_timeout_ms(deadline, 10_000))
            try:
                await page.wait_for_load_state("networkidle", timeout=_remaining_timeout_ms(deadline, 8_000))
            except Exception:
                await page.wait_for_load_state("domcontentloaded", timeout=_remaining_timeout_ms(deadline, 3_000))

            state_dir = Path(settings.artifact_storage_root) / "traces" / test_run_id / agent_id
            state_dir.mkdir(parents=True, exist_ok=True)
            await context.storage_state(path=str(state_dir / "auth-state.json"))
    except Exception as exc:
        status = "failed"
        error_message = str(exc)

    duration_ms = int((time.perf_counter() - started) * 1000)
    screenshot_path = None
    if page.url:
        try:
            screenshot_path = await _capture_screenshot(page, test_run_id, agent_id, step_order)
        except Exception:
            screenshot_path = None

    with db_connection() as connection:
        insert_agent_step(
            connection,
            {
                "agent_id": agent_id,
                "step_order": step_order,
                "action_type": f"auth_{auth_type}",
                "target_selector": auth_profile.get("submit_selector") or auth_profile.get("storage_state_path"),
                "target_text": profile_name,
                "input_value": auth_profile.get("username_value"),
                "url_before": url_before,
                "url_after": page.url or login_url,
                "status": status,
                "error_message": error_message,
                "screenshot_artifact_id": None,
                "dom_snapshot_artifact_id": None,
                "duration_ms": duration_ms,
            },
        )

    publish_event(
        test_run_id,
        "auth_completed" if status == "passed" else "auth_failed",
        {
            "agent_id": agent_id,
            "agent_type": agent_type,
            "auth_profile": profile_name,
            "auth_type": auth_type,
            "status": status,
            "url": page.url or login_url,
            "message": error_message,
            "screenshot_path": screenshot_path,
        },
    )
    return step_order


def _detect_and_store_page_bugs(
    connection,
    project_id: str,
    test_run_id: str,
    agent_id: str,
    url: str,
    status: str,
    error_message: str | None,
    status_code: int | None,
    page_data: dict[str, Any],
    network_idle_timed_out: bool,
    page_crashes: list[str],
    screenshot_path: str,
    dom_snapshot_path: str,
) -> None:
    replay = [{"action_type": "goto", "url": url}]
    detected = []
    if status_code is not None:
        detected.append(detect_http_error(url, status_code))
    if status == "failed" and error_message:
        detected.append(detect_navigation_failure(url, error_message))
    detected.append(
        detect_blank_page(
            url,
            str(page_data.get("visible_text") or ""),
            int(page_data.get("dom_node_count") or 0),
        )
    )
    if network_idle_timed_out:
        detected.append(detect_infinite_loading(url))
    while page_crashes:
        crash_url = page_crashes.pop(0)
        detected.append(detect_page_crash(crash_url))

    for bug in [item for item in detected if item is not None]:
        persist_detected_bug(
            connection,
            project_id=project_id,
            test_run_id=test_run_id,
            agent_id=agent_id,
            bug=bug,
            screenshot_path=screenshot_path,
            dom_snapshot_path=dom_snapshot_path,
            replay=replay,
        )


def _remaining_timeout_ms(deadline: float, fallback_ms: int) -> int:
    remaining_ms = int((deadline - time.monotonic()) * 1000)
    return max(1000, min(fallback_ms, remaining_ms))


def _publish_progress(
    connection,
    test_run_id: str,
    agent_id: str,
    agent_type: str,
    step_order: int,
    max_actions: int,
    visited_count: int,
    queued_count: int,
    current_url: str,
) -> None:
    summary = _run_summary(connection, test_run_id)
    status_counts = _agent_status_counts(connection, test_run_id)
    progress = {
        "agent_id": agent_id,
        "agent_type": agent_type,
        "current_url": current_url,
        "agent_steps_completed": step_order,
        "agent_action_limit": max_actions,
        "agent_progress_percent": min(100, round((step_order / max_actions) * 100)) if max_actions else 100,
        "visited_count": visited_count,
        "queued_count": queued_count,
        "pages_discovered": summary["discovered_pages_count"],
        "steps_completed": summary["agent_steps_count"],
        "browser_logs": summary["browser_logs_count"],
        "network_logs": summary["network_logs_count"],
        "bugs_found": summary["bugs_count"],
        "test_cases": summary["test_cases_count"],
        "status_counts": status_counts,
    }
    merge_test_run_summary(connection, test_run_id, {"progress": progress})
    publish_event(test_run_id, "agent_progress", progress)


def _record_form_steps(
    test_run_id: str,
    agent_id: str,
    agent_type: str,
    url: str,
    page_data: dict[str, Any],
    step_order: int,
    max_actions: int,
    safe_mode: bool,
) -> int:
    for form in page_data.get("forms", [])[:3]:
        if step_order >= max_actions:
            break
        step_order += 1
        action_type = "skip_form_submit" if safe_mode else "inspect_form"
        _insert_inspection_step(
            test_run_id,
            agent_id,
            agent_type,
            step_order,
            action_type,
            form.get("selector"),
            form.get("label") or form.get("text_content"),
            url,
            "skipped" if safe_mode else "passed",
            "Safe mode skips form submission." if safe_mode else None,
        )
    return step_order


def _record_button_steps(
    test_run_id: str,
    agent_id: str,
    agent_type: str,
    url: str,
    page_data: dict[str, Any],
    step_order: int,
    max_actions: int,
    safe_mode: bool,
) -> int:
    buttons = [
        button
        for button in page_data.get("buttons", [])
        if button.get("is_visible") and button.get("is_enabled") and button.get("metadata", {}).get("type") != "submit"
    ]
    for button in buttons[:3]:
        if step_order >= max_actions:
            break
        step_order += 1
        _insert_inspection_step(
            test_run_id,
            agent_id,
            agent_type,
            step_order,
            "skip_button_click" if safe_mode else "inspect_button",
            button.get("selector"),
            button.get("label") or button.get("text_content"),
            url,
            "skipped" if safe_mode else "passed",
            "Safe mode skips arbitrary button clicks." if safe_mode else None,
        )
    return step_order


def _insert_inspection_step(
    test_run_id: str,
    agent_id: str,
    agent_type: str,
    step_order: int,
    action_type: str,
    selector: str | None,
    target_text: str | None,
    url: str,
    status: str = "passed",
    error_message: str | None = None,
) -> None:
    with db_connection() as connection:
        insert_agent_step(
            connection,
            {
                "agent_id": agent_id,
                "step_order": step_order,
                "action_type": action_type,
                "target_selector": selector,
                "target_text": target_text,
                "input_value": None,
                "url_before": url,
                "url_after": url,
                "status": status,
                "error_message": error_message,
                "screenshot_artifact_id": None,
                "dom_snapshot_artifact_id": None,
                "duration_ms": 0,
            },
        )
    publish_event(
        test_run_id,
        "step_completed",
        {
            "agent_id": agent_id,
            "agent_type": agent_type,
            "url": url,
            "action": action_type,
            "status": status,
            "target": target_text or selector,
            "message": error_message,
        },
    )


def _candidate_urls(agent_type: str, current_url: str, page_data: dict[str, Any]) -> list[str]:
    links = page_data.get("links", [])
    ordered = _prioritize_links(agent_type, links)
    urls: list[str] = []
    seen: set[str] = set()
    for link in ordered:
        href = link.get("href")
        if not href:
            continue
        url = normalize_url(current_url, href)
        if url not in seen:
            seen.add(url)
            urls.append(url)
    return urls


def _prioritize_links(agent_type: str, links: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if agent_type == "form":
        return sorted(links, key=lambda link: 0 if _link_matches(link, FORM_TERMS) else 1)
    if agent_type == "navigation":
        return sorted(links, key=lambda link: 0 if _link_matches(link, NAVIGATION_TERMS) else 1)
    if agent_type == "chaos":
        return list(reversed(links))
    return links


def _link_matches(link: dict[str, Any], terms: tuple[str, ...]) -> bool:
    haystack = " ".join(
        str(link.get(key) or "").lower()
        for key in ("href", "label", "text_content", "selector")
    )
    return any(term in haystack for term in terms)


def _default_action_limit(agent_type: str) -> int:
    return {
        "explorer": 45,
        "navigation": 50,
        "form": 35,
        "chaos": 35,
    }.get(agent_type, 40)


def _ai_page_limit(agent_type: str) -> int:
    return {
        "form": 3,
        "explorer": 2,
        "navigation": 1,
        "chaos": 1,
    }.get(agent_type, 1)


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


def _flush_events(
    connection,
    project_id: str,
    test_run_id: str,
    agent_id: str,
    current_url: str,
    console_events: list[dict],
    network_events: list[dict],
) -> None:
    while console_events:
        event = console_events.pop(0)
        if event.get("log_level") in {"error", "warning"}:
            insert_browser_log(connection, {"test_run_id": test_run_id, "agent_id": agent_id, **event})
            bug = detect_console_error(current_url, str(event.get("message") or ""), event.get("source_url"))
            if bug:
                persist_detected_bug(
                    connection,
                    project_id=project_id,
                    test_run_id=test_run_id,
                    agent_id=agent_id,
                    bug=bug,
                    replay=[{"action_type": "goto", "url": current_url}],
                )
            publish_event(test_run_id, "browser_log", {"agent_id": agent_id, **event})
    while network_events:
        event = network_events.pop(0)
        insert_network_log(connection, {"test_run_id": test_run_id, "agent_id": agent_id, **event})
        bug = detect_network_failure(
            str(event.get("request_url") or current_url),
            event.get("status_code"),
            event.get("failure_text"),
            event.get("resource_type"),
        )
        if bug:
            persist_detected_bug(
                connection,
                project_id=project_id,
                test_run_id=test_run_id,
                agent_id=agent_id,
                bug=bug,
                replay=[{"action_type": "goto", "url": current_url}],
            )
        publish_event(test_run_id, "network_failure", {"agent_id": agent_id, **event})


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
    cancelled = connection.execute(
        text(
            """
        SELECT COUNT(*)
        FROM agents
        WHERE test_run_id = :test_run_id
          AND status = 'cancelled'
        """
        ),
        {"test_run_id": test_run_id},
    ).scalar_one()
    if unfinished != 0:
        return

    summary = _run_summary(connection, test_run_id)
    status = "failed" if failed else "cancelled" if cancelled else "completed"
    merge_test_run_summary(
        connection,
        test_run_id,
        {"completed_summary": {**summary, "status_counts": _agent_status_counts(connection, test_run_id)}},
    )
    update_test_run_status(connection, test_run_id, status, completed=True)
    publish_event(
        test_run_id,
        "test_run_completed",
        {
            "test_run_id": test_run_id,
            "status": status,
            "bugs_found": summary["bugs_count"],
            "pages_discovered": summary["discovered_pages_count"],
            "steps_completed": summary["agent_steps_count"],
            "test_cases_created": summary["test_cases_count"],
            "status_counts": _agent_status_counts(connection, test_run_id),
        },
    )


def _run_summary(connection, test_run_id: str) -> dict[str, int]:
    agents = connection.execute(
        text("SELECT COUNT(*) FROM agents WHERE test_run_id = :test_run_id"),
        {"test_run_id": test_run_id},
    ).scalar_one()
    discovered_pages = connection.execute(
        text("SELECT COUNT(*) FROM discovered_pages WHERE test_run_id = :test_run_id"),
        {"test_run_id": test_run_id},
    ).scalar_one()
    agent_steps = connection.execute(
        text(
            """
            SELECT COUNT(*)
            FROM agent_steps
            JOIN agents ON agents.id = agent_steps.agent_id
            WHERE agents.test_run_id = :test_run_id
            """
        ),
        {"test_run_id": test_run_id},
    ).scalar_one()
    browser_logs = connection.execute(
        text("SELECT COUNT(*) FROM browser_logs WHERE test_run_id = :test_run_id"),
        {"test_run_id": test_run_id},
    ).scalar_one()
    network_logs = connection.execute(
        text("SELECT COUNT(*) FROM network_logs WHERE test_run_id = :test_run_id"),
        {"test_run_id": test_run_id},
    ).scalar_one()
    bugs = connection.execute(
        text("SELECT COUNT(*) FROM bugs WHERE test_run_id = :test_run_id"),
        {"test_run_id": test_run_id},
    ).scalar_one()
    test_cases = connection.execute(
        text("SELECT COUNT(*) FROM test_cases WHERE test_run_id = :test_run_id"),
        {"test_run_id": test_run_id},
    ).scalar_one()
    return {
        "agent_count": int(agents),
        "discovered_pages_count": int(discovered_pages),
        "agent_steps_count": int(agent_steps),
        "browser_logs_count": int(browser_logs),
        "network_logs_count": int(network_logs),
        "bugs_count": int(bugs),
        "test_cases_count": int(test_cases),
    }


def _agent_status_counts(connection, test_run_id: str) -> dict[str, int]:
    rows = connection.execute(
        text(
            """
            SELECT status, COUNT(*)
            FROM agents
            WHERE test_run_id = :test_run_id
            GROUP BY status
            """
        ),
        {"test_run_id": test_run_id},
    ).all()
    return {str(status): int(count) for status, count in rows}
