from __future__ import annotations

import asyncio
import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any

from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from bugswarm_worker.ai.consensus.council import build_consensus
from bugswarm_worker.ai.providers.base import EvidencePacket, ProviderKey, ProviderResult
from bugswarm_worker.ai.providers.gemini import GeminiJSONProvider
from bugswarm_worker.ai.providers.http_json import OpenAICompatibleJSONProvider
from bugswarm_worker.browser.scope import is_url_allowed, normalize_url
from bugswarm_worker.config import settings
from bugswarm_worker.db import (
    db_connection,
    fetch_provider_configs,
    insert_agent_step,
    insert_model_response,
    insert_reasoning_session,
    insert_test_case,
    insert_test_step,
    merge_test_run_summary,
    test_case_exists,
    update_test_case_status,
)
from bugswarm_worker.detection.persistence import persist_detected_bug
from bugswarm_worker.detection.rules import detect_element_interaction_failure
from bugswarm_worker.events import publish_event

DEFAULT_PROVIDER_KEYS = ["groq", "gptoss", "gemini"]
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
DESTRUCTIVE_TERMS = (
    "delete",
    "remove",
    "destroy",
    "purchase",
    "pay",
    "payment",
    "checkout",
    "submit order",
    "confirm",
    "logout",
)


@dataclass(frozen=True)
class AIGenerationResult:
    test_cases_created: int
    agent_steps_created: int


async def generate_and_execute_tests_for_page(
    *,
    page,
    project_id: str,
    test_run_id: str,
    agent_id: str,
    base_url: str,
    page_data: dict[str, Any],
    provider_keys: list[str],
    consensus_mode: str,
    safe_mode: bool,
    allowed_patterns: list[str],
    excluded_patterns: list[str],
    step_order: int,
    deadline: float,
) -> AIGenerationResult:
    evidence = EvidencePacket(
        url=page.url,
        title=page_data.get("title"),
        forms=_compact_elements(page_data.get("forms", []), limit=8),
        buttons=_compact_elements(page_data.get("buttons", []), limit=12),
        links=_compact_elements(page_data.get("links", []), limit=12),
        inputs=_compact_elements(page_data.get("inputs", []), limit=16),
        console_errors=[],
        network_failures=[],
    )
    prompt_hash = _prompt_hash(evidence)

    with db_connection() as connection:
        if test_case_exists(connection, test_run_id, prompt_hash):
            return AIGenerationResult(test_cases_created=0, agent_steps_created=0)

    publish_event(
        test_run_id,
        "ai_generation_started",
        {"agent_id": agent_id, "url": evidence.url, "providers": provider_keys or DEFAULT_PROVIDER_KEYS},
    )

    provider_results = await _run_providers(project_id, provider_keys or DEFAULT_PROVIDER_KEYS, evidence)
    consensus = build_consensus(provider_results)
    accepted_cases = _validate_test_cases(consensus.accepted_test_cases, evidence.url)
    source = "ai"
    if not accepted_cases:
        accepted_cases = _seed_test_cases(evidence, safe_mode)
        source = "ai_seed"

    with db_connection() as connection:
        reasoning_session_id = insert_reasoning_session(
            connection,
            {
                "test_run_id": test_run_id,
                "task_type": "test_generation",
                "prompt_fingerprint": prompt_hash,
                "consensus_status": consensus.status,
                "consensus_mode": consensus_mode,
                "final_rationale": consensus.final_rationale,
                "requires_human_review": consensus.requires_human_review,
                "metadata": {
                    "url": evidence.url,
                    "vote_counts": consensus.vote_counts,
                    "provider_summaries": consensus.provider_summaries,
                    "seeded_fallback": source == "ai_seed",
                },
            },
        )
        for result in provider_results:
            insert_model_response(
                connection,
                {
                    "reasoning_session_id": reasoning_session_id,
                    "provider_key": result.provider,
                    "model_name": result.model,
                    "status": result.status,
                    "confidence": result.confidence,
                    "vote": result.vote,
                    "rationale_summary": result.rationale_summary,
                    "output": {"risks": result.risks, "test_cases": result.test_cases},
                    "error_message": result.error_message,
                    "latency_ms": result.latency_ms,
                    "token_usage": {},
                },
            )

        stored_cases = []
        for test_case in accepted_cases[:4]:
            test_case_id = insert_test_case(
                connection,
                {
                    "project_id": project_id,
                    "test_run_id": test_run_id,
                    "name": test_case["test_name"],
                    "description": test_case.get("goal"),
                    "source": source,
                    "priority": test_case.get("priority", "medium"),
                    "status": "generated",
                    "expected_result": test_case.get("expected_result"),
                    "ai_prompt_hash": prompt_hash,
                },
            )
            for index, step in enumerate(test_case.get("steps", [])[:8], start=1):
                insert_test_step(
                    connection,
                    {
                        "test_case_id": test_case_id,
                        "step_order": index,
                        "action_type": step["action"],
                        "selector_hint": step.get("selector_hint") or step.get("target"),
                        "selector_resolved": None,
                        "input_value": step.get("value"),
                        "expected_observation": step.get("expected_observation"),
                        "timeout_ms": int(step.get("timeout_ms") or 5000),
                    },
                )
            stored_cases.append((test_case_id, test_case))

        merge_test_run_summary(
            connection,
            test_run_id,
            {
                "ai_generation": {
                    "last_url": evidence.url,
                    "last_consensus_status": consensus.status,
                    "last_reasoning_session_id": reasoning_session_id,
                    "test_cases_created": len(stored_cases),
                    "seeded_fallback": source == "ai_seed",
                }
            },
        )

    publish_event(
        test_run_id,
        "llm_consensus_completed",
        {
            "reasoning_session_id": reasoning_session_id,
            "providers": [result.provider for result in provider_results],
            "consensus_status": consensus.status,
            "agreement_count": consensus.vote_counts.get("approve", 0),
            "test_cases_created": len(stored_cases),
        },
    )

    execution_steps = 0
    for test_case_id, test_case in stored_cases:
        if time.monotonic() >= deadline:
            break
        created = await _execute_test_case(
            page=page,
            project_id=project_id,
            test_run_id=test_run_id,
            agent_id=agent_id,
            test_case_id=test_case_id,
            test_case=test_case,
            base_url=base_url,
            allowed_patterns=allowed_patterns,
            excluded_patterns=excluded_patterns,
            safe_mode=safe_mode,
            step_order=step_order + execution_steps,
            deadline=deadline,
        )
        execution_steps += created

    publish_event(
        test_run_id,
        "ai_tests_generated",
        {
            "agent_id": agent_id,
            "url": evidence.url,
            "test_cases_created": len(stored_cases),
            "steps_completed": execution_steps,
        },
    )
    return AIGenerationResult(test_cases_created=len(stored_cases), agent_steps_created=execution_steps)


def page_supports_ai_generation(page_data: dict[str, Any]) -> bool:
    return bool(page_data.get("forms") or page_data.get("inputs") or page_data.get("buttons") or page_data.get("links"))


async def _run_providers(project_id: str, provider_keys: list[str], evidence: EvidencePacket) -> list[ProviderResult]:
    with db_connection() as connection:
        configs = fetch_provider_configs(connection, project_id, provider_keys)
    config_by_key = {config["provider_key"]: config for config in configs}
    results: list[ProviderResult] = []
    providers = []

    for provider_key in provider_keys:
        config = config_by_key.get(provider_key)
        provider = _build_provider(provider_key, config)
        if isinstance(provider, ProviderResult):
            results.append(provider)
        elif provider is not None:
            providers.append(provider)

    if providers:
        results.extend(await asyncio.gather(*(provider.generate_tests(evidence) for provider in providers)))
    return results


def _build_provider(provider_key: str, config: dict[str, Any] | None):
    model = str(config.get("model_name") if config else "") if config else ""
    timeout_seconds = int(config.get("timeout_seconds") or 30) if config else 30
    max_retries = int(config.get("max_retries") or 2) if config else 2
    enabled = bool(config.get("is_enabled")) if config else False

    if provider_key == "groq":
        if not enabled or not settings.groq_api_key:
            return _disabled_result("groq", model or settings.groq_model)
        return OpenAICompatibleJSONProvider(
            "groq",
            model or settings.groq_model,
            str(config.get("base_url") or GROQ_BASE_URL),
            settings.groq_api_key,
            timeout_seconds,
            max_retries,
        )
    if provider_key == "gptoss":
        base_url = str(config.get("base_url") or settings.gptoss_base_url) if config else settings.gptoss_base_url
        if not enabled or not base_url:
            return _disabled_result("gptoss", model or settings.gptoss_model)
        return OpenAICompatibleJSONProvider(
            "gptoss",
            model or settings.gptoss_model,
            base_url,
            None,
            timeout_seconds,
            max_retries,
        )
    if provider_key == "openrouter":
        if not enabled or not settings.openrouter_api_key:
            return _disabled_result("openrouter", model or settings.openrouter_model)
        return OpenAICompatibleJSONProvider(
            "openrouter",
            model or settings.openrouter_model,
            str(config.get("base_url") or settings.openrouter_base_url),
            settings.openrouter_api_key,
            timeout_seconds,
            max_retries,
        )
    if provider_key == "gemini":
        if not enabled or not settings.gemini_api_key:
            return _disabled_result("gemini", model or settings.gemini_model)
        return GeminiJSONProvider(model or settings.gemini_model, settings.gemini_api_key, timeout_seconds, max_retries)
    return None


def _disabled_result(provider: ProviderKey, model: str) -> ProviderResult:
    return ProviderResult(
        provider=provider,
        model=model,
        status="disabled",
        confidence=0.0,
        vote="needs_more_evidence",
        rationale_summary="Provider is not configured for this project.",
        error_message="Provider is disabled or missing credentials.",
    )


def _validate_test_cases(raw_cases: list[dict[str, Any]], current_url: str) -> list[dict[str, Any]]:
    valid_cases: list[dict[str, Any]] = []
    for raw_case in raw_cases:
        steps = []
        for raw_step in raw_case.get("steps", []):
            action = str(raw_step.get("action") or "").strip().lower()
            if action not in {"goto", "fill", "click", "assert_text"}:
                continue
            steps.append(
                {
                    "action": action,
                    "target": str(raw_step.get("target") or raw_step.get("selector_hint") or current_url),
                    "selector_hint": str(raw_step.get("selector_hint") or raw_step.get("target") or ""),
                    "value": str(raw_step.get("value") or ""),
                    "expected_observation": str(raw_step.get("expected_observation") or ""),
                    "timeout_ms": int(raw_step.get("timeout_ms") or 5000),
                }
            )
        if not steps:
            continue
        valid_cases.append(
            {
                "test_name": str(raw_case.get("test_name") or raw_case.get("name") or "AI generated test")[:220],
                "goal": str(raw_case.get("goal") or raw_case.get("description") or "")[:2000],
                "priority": _priority(raw_case.get("priority")),
                "steps": steps[:8],
                "expected_result": str(raw_case.get("expected_result") or "Expected behavior remains stable.")[:2000],
            }
        )
    return valid_cases


def _seed_test_cases(evidence: EvidencePacket, safe_mode: bool) -> list[dict[str, Any]]:
    cases = [
        {
            "test_name": f"Smoke load {evidence.title or evidence.url}",
            "goal": "Verify the discovered page loads and exposes visible content.",
            "priority": "medium",
            "steps": [
                {"action": "goto", "target": evidence.url, "selector_hint": evidence.url},
                {
                    "action": "assert_text",
                    "target": evidence.title or "",
                    "selector_hint": evidence.title or "",
                    "expected_observation": "Page title or body content should be visible.",
                },
            ],
            "expected_result": "The page loads without navigation or rendering failures.",
        }
    ]
    if evidence.inputs:
        fields = [input_item for input_item in evidence.inputs if input_item.get("is_visible")][:4]
        steps = [{"action": "goto", "target": evidence.url, "selector_hint": evidence.url}]
        for field in fields:
            selector = field.get("selector") or field.get("label") or field.get("placeholder") or "input"
            steps.append(
                {
                    "action": "fill",
                    "target": selector,
                    "selector_hint": selector,
                    "value": _negative_value(field),
                    "expected_observation": "The form should validate invalid or edge-case input.",
                }
            )
        if not safe_mode:
            submit = next((button for button in evidence.buttons if _looks_like_submit(button)), None)
            if submit:
                selector = submit.get("selector") or submit.get("label") or submit.get("text_content") or "button"
                steps.append(
                    {
                        "action": "click",
                        "target": selector,
                        "selector_hint": selector,
                        "expected_observation": "Validation feedback should appear without a crash.",
                    }
                )
        cases.append(
            {
                "test_name": "Negative form validation",
                "goal": "Exercise visible form inputs with invalid or boundary values.",
                "priority": "high",
                "steps": steps,
                "expected_result": "The page should show validation feedback and remain usable.",
            }
        )
    return cases


async def _execute_test_case(
    *,
    page,
    project_id: str,
    test_run_id: str,
    agent_id: str,
    test_case_id: str,
    test_case: dict[str, Any],
    base_url: str,
    allowed_patterns: list[str],
    excluded_patterns: list[str],
    safe_mode: bool,
    step_order: int,
    deadline: float,
) -> int:
    created_steps = 0
    failed = False
    skipped = False
    for step in test_case.get("steps", []):
        if time.monotonic() >= deadline:
            skipped = True
            break
        step_order += 1
        created_steps += 1
        status = "passed"
        error_message = None
        url_before = page.url
        started = time.perf_counter()
        action = step["action"]
        target = step.get("target") or step.get("selector_hint") or ""
        selector_hint = step.get("selector_hint") or target
        try:
            if action == "goto":
                destination = normalize_url(base_url, target or base_url)
                if not is_url_allowed(base_url, destination, allowed_patterns, excluded_patterns):
                    status = "skipped"
                    error_message = "Generated URL was outside the configured project scope."
                else:
                    await page.goto(destination, wait_until="domcontentloaded", timeout=_remaining_timeout_ms(deadline, 10_000))
            elif action == "fill":
                locator = await _resolve_fill_locator(page, selector_hint)
                await locator.fill(step.get("value") or "", timeout=_remaining_timeout_ms(deadline, 5_000))
            elif action == "click":
                if safe_mode and _is_destructive(selector_hint):
                    status = "skipped"
                    error_message = "Safe mode skipped a potentially destructive generated click."
                else:
                    locator = await _resolve_click_locator(page, selector_hint)
                    await locator.click(timeout=_remaining_timeout_ms(deadline, 5_000))
            elif action == "assert_text":
                text = target or step.get("expected_observation")
                if text:
                    await page.get_by_text(text, exact=False).first.wait_for(timeout=_remaining_timeout_ms(deadline, 3_000))
        except Exception as exc:
            failed = True
            status = "failed"
            error_message = str(exc)

        with db_connection() as connection:
            insert_agent_step(
                connection,
                {
                    "agent_id": agent_id,
                    "step_order": step_order,
                    "action_type": f"ai_{action}",
                    "target_selector": selector_hint,
                    "target_text": target,
                    "input_value": step.get("value") or None,
                    "url_before": url_before,
                    "url_after": page.url,
                    "status": status,
                    "error_message": error_message,
                    "screenshot_artifact_id": None,
                    "dom_snapshot_artifact_id": None,
                    "duration_ms": int((time.perf_counter() - started) * 1000),
                },
            )
            if status == "failed" and error_message:
                persist_detected_bug(
                    connection,
                    project_id=project_id,
                    test_run_id=test_run_id,
                    agent_id=agent_id,
                    bug=detect_element_interaction_failure(page.url, f"ai_{action}", selector_hint, error_message),
                    replay=[
                        {
                            "action_type": f"ai_{action}",
                            "selector": selector_hint,
                            "selector_hint": selector_hint,
                            "input_value": step.get("value") or None,
                            "url": url_before,
                        }
                    ],
                )
        publish_event(
            test_run_id,
            "ai_step_completed",
            {
                "agent_id": agent_id,
                "test_case_id": test_case_id,
                "action": action,
                "status": status,
                "target": selector_hint,
                "message": error_message,
            },
        )
        if status == "skipped":
            skipped = True

    final_status = "failed" if failed else "skipped" if skipped else "passed"
    with db_connection() as connection:
        update_test_case_status(connection, test_case_id, final_status)
    publish_event(
        test_run_id,
        "ai_test_completed",
        {"agent_id": agent_id, "test_case_id": test_case_id, "status": final_status, "title": test_case["test_name"]},
    )
    return created_steps


async def _resolve_fill_locator(page, selector_hint: str):
    hints = [selector_hint.strip()] if selector_hint else []
    for hint in hints:
        if _looks_like_css(hint):
            try:
                locator = page.locator(hint).first
                if await locator.count():
                    return locator
            except Exception:
                pass
        for candidate in (page.get_by_label(hint).first, page.get_by_placeholder(hint).first):
            try:
                await candidate.wait_for(timeout=500)
                return candidate
            except PlaywrightTimeoutError:
                continue
    return page.locator("input, textarea, select").first


async def _resolve_click_locator(page, selector_hint: str):
    hint = selector_hint.strip()
    if hint and _looks_like_css(hint):
        try:
            return page.locator(hint).first
        except Exception:
            pass
    if hint:
        for candidate in (page.get_by_role("button", name=hint).first, page.get_by_text(hint, exact=False).first):
            try:
                await candidate.wait_for(timeout=500)
                return candidate
            except PlaywrightTimeoutError:
                continue
    return page.locator("button, [role='button'], a").first


def _compact_elements(elements: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    compacted = []
    for element in elements[:limit]:
        compacted.append(
            {
                "element_type": element.get("element_type"),
                "selector": element.get("selector"),
                "label": element.get("label"),
                "placeholder": element.get("placeholder"),
                "text_content": element.get("text_content"),
                "href": element.get("href"),
                "is_visible": element.get("is_visible"),
                "is_enabled": element.get("is_enabled"),
                "metadata": element.get("metadata", {}),
            }
        )
    return compacted


def _prompt_hash(evidence: EvidencePacket) -> str:
    payload = {
        "url": evidence.url,
        "title": evidence.title,
        "forms": evidence.forms,
        "buttons": evidence.buttons,
        "links": evidence.links,
        "inputs": evidence.inputs,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=True).encode("utf-8")).hexdigest()


def _remaining_timeout_ms(deadline: float, fallback_ms: int) -> int:
    return max(1000, min(fallback_ms, int((deadline - time.monotonic()) * 1000)))


def _priority(value: Any) -> str:
    priority = str(value or "medium").lower()
    return priority if priority in {"low", "medium", "high"} else "medium"


def _looks_like_css(value: str) -> bool:
    lowered = value.lower()
    return lowered.startswith(("#", ".", "[", "input", "textarea", "select", "button", "a[", "form"))


def _looks_like_submit(button: dict[str, Any]) -> bool:
    text_value = " ".join(str(button.get(key) or "").lower() for key in ("label", "text_content", "selector"))
    return "submit" in text_value or "login" in text_value or "search" in text_value or "send" in text_value


def _negative_value(field: dict[str, Any]) -> str:
    haystack = " ".join(str(field.get(key) or "").lower() for key in ("label", "placeholder", "selector", "metadata"))
    if "email" in haystack:
        return "not-an-email"
    if "password" in haystack:
        return "123"
    if "phone" in haystack:
        return "abc"
    if "search" in haystack:
        return "\"' OR 1=1 --"
    return "###"


def _is_destructive(value: str) -> bool:
    lowered = value.lower()
    return any(term in lowered for term in DESTRUCTIVE_TERMS)
