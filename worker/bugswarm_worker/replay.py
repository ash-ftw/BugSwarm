from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any

from playwright.async_api import async_playwright

from bugswarm_worker.config import settings
from bugswarm_worker.db import db_connection, fetch_bug_with_replay, insert_bug_artifact, insert_report
from bugswarm_worker.events import publish_event


async def replay_bug(job: dict[str, Any]) -> dict[str, Any]:
    bug_id = str(job["bug_id"])
    with db_connection() as connection:
        bug = fetch_bug_with_replay(connection, bug_id)
    if bug is None:
        raise ValueError(f"Bug {bug_id} was not found.")

    test_run_id = str(bug["test_run_id"])
    replay_steps = bug.get("replay_steps", [])
    publish_event(test_run_id, "replay_started", {"bug_id": bug_id, "steps": len(replay_steps)})

    started = time.perf_counter()
    screenshot_dir = Path(settings.artifact_storage_root) / "screenshots" / test_run_id / "replay" / bug_id
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    step_results = []
    status = "passed"

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(ignore_https_errors=True, viewport={"width": 1440, "height": 900})
        page = await context.new_page()
        try:
            for step in replay_steps:
                step_started = time.perf_counter()
                result = {
                    "step_order": step["step_order"],
                    "action_type": step["action_type"],
                    "target": step.get("selector") or step.get("selector_hint") or step.get("url"),
                    "status": "passed",
                    "message": None,
                    "screenshot_path": None,
                    "duration_ms": 0,
                }
                try:
                    await _execute_replay_step(page, step, bug)
                except Exception as exc:
                    status = "failed"
                    result["status"] = "failed"
                    result["message"] = str(exc)
                screenshot_path = screenshot_dir / f"step-{int(step['step_order']):04d}.png"
                try:
                    await page.screenshot(path=str(screenshot_path), full_page=True)
                    result["screenshot_path"] = str(screenshot_path)
                    with db_connection() as connection:
                        insert_bug_artifact(
                            connection,
                            {
                                "bug_id": bug_id,
                                "artifact_type": "replay_screenshot",
                                "file_path": str(screenshot_path),
                                "mime_type": "image/png",
                                "file_size_bytes": screenshot_path.stat().st_size if screenshot_path.exists() else None,
                                "label": f"Replay step {step['step_order']}",
                            },
                        )
                except Exception:
                    pass
                result["duration_ms"] = int((time.perf_counter() - step_started) * 1000)
                step_results.append(result)
                publish_event(test_run_id, "replay_step_completed", {"bug_id": bug_id, **result})
                if status == "failed":
                    break
        finally:
            await context.close()
            await browser.close()

    attempt = {
        "bug_id": bug_id,
        "status": status,
        "duration_ms": int((time.perf_counter() - started) * 1000),
        "steps": step_results,
    }
    with db_connection() as connection:
        report_id = insert_report(
            connection,
            {
                "test_run_id": test_run_id,
                "report_type": "replay_attempt",
                "file_path": None,
                "content": attempt,
            },
        )
    publish_event(test_run_id, "replay_completed", {"bug_id": bug_id, "report_id": report_id, "status": status})
    return {**attempt, "report_id": report_id}


def generate_playwright_script_for_bug(bug: dict[str, Any]) -> str:
    title = _quote(str(bug.get("title") or "Bug replay"))
    lines = [
        "import { test, expect } from '@playwright/test';",
        "",
        f"test('Replay: {title}', async ({{ page }}) => {{",
    ]
    replay_steps = bug.get("replay_steps") or []
    if not replay_steps and bug.get("affected_url"):
        replay_steps = [{"action_type": "goto", "url": bug["affected_url"]}]
    for step in replay_steps:
        lines.extend(_script_lines_for_step(step, bug))
    expected = bug.get("expected_result")
    if expected:
        lines.append(f"  // Expected: {_comment(expected)}")
    actual = bug.get("actual_result")
    if actual:
        lines.append(f"  // Observed failure: {_comment(actual)}")
    lines.append("});")
    return "\n".join(lines) + "\n"


async def _execute_replay_step(page, step: dict[str, Any], bug: dict[str, Any]) -> None:
    action = str(step.get("action_type") or "goto").replace("ai_", "")
    target_url = step.get("url") or bug.get("affected_url") or bug.get("base_url")
    selector = step.get("selector") or step.get("selector_hint")
    if action in {"goto", "navigation"}:
        await page.goto(target_url, wait_until="domcontentloaded", timeout=15_000)
        return
    if action in {"fill", "input"}:
        locator = _locator_for(page, selector)
        await locator.fill(step.get("input_value") or "", timeout=5_000)
        return
    if action in {"click", "button"}:
        locator = _locator_for(page, selector)
        await locator.click(timeout=5_000)
        return
    if action == "assert_text":
        text = step.get("expected_result") or selector or ""
        if text:
            await expect_text(page, text)
        return
    await page.goto(target_url, wait_until="domcontentloaded", timeout=15_000)


async def expect_text(page, text: str) -> None:
    await page.get_by_text(text, exact=False).first.wait_for(timeout=5_000)


def _locator_for(page, selector: str | None):
    if selector and _looks_like_css(selector):
        return page.locator(selector).first
    if selector:
        return page.get_by_text(selector, exact=False).first
    return page.locator("button, input, textarea, select, a").first


def _script_lines_for_step(step: dict[str, Any], bug: dict[str, Any]) -> list[str]:
    action = str(step.get("action_type") or "goto").replace("ai_", "")
    selector = step.get("selector") or step.get("selector_hint")
    url = step.get("url") or bug.get("affected_url") or bug.get("base_url")
    if action in {"goto", "navigation"}:
        return [f"  await page.goto('{_quote(str(url or ''))}');"]
    if action in {"fill", "input"}:
        return [f"  await {_locator_script(selector)}.fill('{_quote(str(step.get('input_value') or ''))}');"]
    if action in {"click", "button"}:
        return [f"  await {_locator_script(selector)}.click();"]
    if action == "assert_text":
        text = step.get("expected_result") or selector or ""
        return [f"  await expect(page.getByText('{_quote(str(text))}')).toBeVisible();"]
    return [f"  // Unsupported replay action: {_comment(action)}"]


def _locator_script(selector: str | None) -> str:
    if selector and _looks_like_css(selector):
        return f"page.locator('{_quote(selector)}')"
    if selector:
        return f"page.getByText('{_quote(selector)}')"
    return "page.locator('button, input, textarea, select, a').first()"


def _looks_like_css(value: str) -> bool:
    lowered = value.strip().lower()
    return lowered.startswith(("#", ".", "[", "input", "textarea", "select", "button", "a[", "form"))


def _quote(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")


def _comment(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()[:500]
