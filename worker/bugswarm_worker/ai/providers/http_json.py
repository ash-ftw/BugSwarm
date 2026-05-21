from __future__ import annotations

import time
from typing import Any

import httpx

from bugswarm_worker.ai.providers.base import BugEvidencePacket, BugValidationResult, EvidencePacket, ProviderKey, ProviderResult


class OpenAICompatibleJSONProvider:
    def __init__(
        self,
        provider_key: ProviderKey,
        model: str,
        base_url: str,
        api_key: str | None = None,
        timeout_seconds: int = 30,
        max_retries: int = 2,
    ) -> None:
        self.provider_key = provider_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    async def generate_tests(self, evidence: EvidencePacket) -> ProviderResult:
        started = time.perf_counter()
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "Return only valid JSON for the BugSwarm reasoning council."},
                {"role": "user", "content": build_prompt(self.provider_key, evidence)},
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await _post_with_retries(
                    client,
                    f"{self.base_url}/chat/completions",
                    headers,
                    payload,
                    self.max_retries,
                )
            body = response.json()
            content = body["choices"][0]["message"]["content"]
            parsed = httpx.Response(200, content=content).json()
            return ProviderResult(
                provider=self.provider_key,
                model=self.model,
                status="completed",
                confidence=float(parsed.get("confidence", 0.0)),
                vote=parsed.get("vote", "needs_more_evidence"),
                rationale_summary=parsed.get("rationale_summary", ""),
                risks=parsed.get("risks", []),
                test_cases=parsed.get("test_cases", []),
                latency_ms=int((time.perf_counter() - started) * 1000),
            )
        except Exception as exc:  # Provider failures degrade consensus instead of failing the run.
            return ProviderResult(
                provider=self.provider_key,
                model=self.model,
                status="failed",
                confidence=0.0,
                vote="needs_more_evidence",
                rationale_summary="Provider did not return a usable response.",
                error_message=str(exc),
                latency_ms=int((time.perf_counter() - started) * 1000),
            )

    async def validate_bug(self, evidence: BugEvidencePacket) -> BugValidationResult:
        started = time.perf_counter()
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "Return only valid JSON for BugSwarm bug validation."},
                {"role": "user", "content": build_bug_validation_prompt(self.provider_key, evidence)},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await _post_with_retries(
                    client,
                    f"{self.base_url}/chat/completions",
                    headers,
                    payload,
                    self.max_retries,
                )
            body = response.json()
            content = body["choices"][0]["message"]["content"]
            parsed = httpx.Response(200, content=content).json()
            return _bug_validation_result(self.provider_key, self.model, parsed, int((time.perf_counter() - started) * 1000))
        except Exception as exc:
            return BugValidationResult(
                provider=self.provider_key,
                model=self.model,
                status="failed",
                confidence=0.0,
                vote="needs_more_evidence",
                severity=evidence.severity,
                rationale_summary="Provider did not return a usable bug validation response.",
                error_message=str(exc),
                latency_ms=int((time.perf_counter() - started) * 1000),
            )


def build_prompt(provider_key: str, evidence: EvidencePacket) -> str:
    return f"""
You are a software QA test generation agent.
You are one member of a three-model reasoning council.
Your provider key is: {provider_key}.

Target page:
URL: {evidence.url}
Title: {evidence.title or ""}

Visible forms:
{evidence.forms}

Buttons:
{evidence.buttons}

Links:
{evidence.links}

Inputs:
{evidence.inputs}

Console errors:
{evidence.console_errors}

Network failures:
{evidence.network_failures}

Rules:
- Return valid JSON only.
- Match this shape exactly:
  {{
    "confidence": 0.0,
    "vote": "approve|reject|needs_more_evidence",
    "rationale_summary": "short user-facing summary",
    "risks": ["short risk"],
    "test_cases": [
      {{
        "test_name": "short name",
        "goal": "what this validates",
        "priority": "low|medium|high",
        "steps": [
          {{
            "action": "goto|fill|click|assert_text",
            "target": "URL or selector hint",
            "selector_hint": "CSS selector, role, label, or text hint",
            "value": "input value when filling",
            "expected_observation": "what should be true"
          }}
        ],
        "expected_result": "expected user-visible result"
      }}
    ]
  }}
- Do not include destructive actions.
- Stay within the configured domain.
- Include negative form values when a form is present.
- Include concise rationale_summary only, not hidden chain-of-thought.
- Vote approve, reject, or needs_more_evidence.
""".strip()


def build_bug_validation_prompt(provider_key: str, evidence: BugEvidencePacket) -> str:
    return f"""
You are a software QA bug validation agent.
You are one member of a BugSwarm reasoning council.
Your provider key is: {provider_key}.

Bug evidence:
ID: {evidence.bug_id}
Title: {evidence.title}
Category: {evidence.category}
Current severity: {evidence.severity}
URL: {evidence.affected_url or ""}
Expected: {evidence.expected_result or ""}
Actual: {evidence.actual_result or ""}

Replay steps:
{evidence.replay_steps}

Artifacts:
{evidence.artifacts}

Browser logs:
{evidence.browser_logs}

Network logs:
{evidence.network_logs}

Rules:
- Return valid JSON only.
- Match this shape exactly:
  {{
    "confidence": 0.0,
    "vote": "valid_bug|false_positive|needs_more_evidence",
    "severity": "critical|high|medium|low",
    "rationale_summary": "short reason for the vote",
    "ai_summary": "user-facing bug summary",
    "suggested_fix": "short engineering fix suggestion",
    "risks": ["short risk or uncertainty"]
  }}
- Use evidence, replayability, logs, and user impact to classify severity.
- Vote false_positive only when evidence strongly suggests the issue is not a real product bug.
- Include concise summaries only, not hidden chain-of-thought.
""".strip()


def _bug_validation_result(
    provider: ProviderKey,
    model: str,
    parsed: dict[str, Any],
    latency_ms: int,
) -> BugValidationResult:
    vote = str(parsed.get("vote") or "needs_more_evidence")
    if vote not in {"valid_bug", "false_positive", "needs_more_evidence"}:
        vote = "needs_more_evidence"
    severity = str(parsed.get("severity") or "medium").lower()
    if severity not in {"critical", "high", "medium", "low"}:
        severity = "medium"
    return BugValidationResult(
        provider=provider,
        model=model,
        status="completed",
        confidence=float(parsed.get("confidence", 0.0)),
        vote=vote,  # type: ignore[arg-type]
        severity=severity,
        rationale_summary=str(parsed.get("rationale_summary") or ""),
        ai_summary=str(parsed.get("ai_summary") or "")[:2000] or None,
        suggested_fix=str(parsed.get("suggested_fix") or "")[:2000] or None,
        risks=[str(item)[:300] for item in parsed.get("risks", []) if str(item).strip()],
        latency_ms=latency_ms,
    )


async def _post_with_retries(
    client: httpx.AsyncClient,
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    max_retries: int,
) -> httpx.Response:
    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code in {408, 409, 425, 429} or response.status_code >= 500:
                response.raise_for_status()
            response.raise_for_status()
            return response
        except (httpx.TimeoutException, httpx.HTTPStatusError) as exc:
            last_error = exc
            if attempt >= max_retries:
                break
            await _sleep_backoff(attempt)
    assert last_error is not None
    raise last_error


async def _sleep_backoff(attempt: int) -> None:
    import asyncio

    await asyncio.sleep(min(4.0, 0.5 * (2**attempt)))
