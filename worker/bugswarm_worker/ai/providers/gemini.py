from __future__ import annotations

import time
from typing import Any

import httpx

from bugswarm_worker.ai.providers.base import BugEvidencePacket, BugValidationResult, EvidencePacket, ProviderResult
from bugswarm_worker.ai.providers.http_json import build_bug_validation_prompt, build_prompt


class GeminiJSONProvider:
    provider_key = "gemini"

    def __init__(
        self,
        model: str,
        api_key: str,
        timeout_seconds: int = 30,
        max_retries: int = 2,
    ) -> None:
        self.model = model
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    async def generate_tests(self, evidence: EvidencePacket) -> ProviderResult:
        started = time.perf_counter()
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent?key={self.api_key}"
        )
        payload: dict[str, Any] = {
            "contents": [{"parts": [{"text": build_prompt(self.provider_key, evidence)}]}],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json",
            },
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await _post_with_retries(client, url, payload, self.max_retries)
            body = response.json()
            content = body["candidates"][0]["content"]["parts"][0]["text"]
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
        except Exception as exc:
            return ProviderResult(
                provider=self.provider_key,
                model=self.model,
                status="failed",
                confidence=0.0,
                vote="needs_more_evidence",
                rationale_summary="Gemini did not return a usable response.",
                error_message=str(exc),
                latency_ms=int((time.perf_counter() - started) * 1000),
            )

    async def validate_bug(self, evidence: BugEvidencePacket) -> BugValidationResult:
        started = time.perf_counter()
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent?key={self.api_key}"
        )
        payload: dict[str, Any] = {
            "contents": [{"parts": [{"text": build_bug_validation_prompt(self.provider_key, evidence)}]}],
            "generationConfig": {
                "temperature": 0.1,
                "responseMimeType": "application/json",
            },
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await _post_with_retries(client, url, payload, self.max_retries)
            body = response.json()
            content = body["candidates"][0]["content"]["parts"][0]["text"]
            parsed = httpx.Response(200, content=content).json()
            vote = str(parsed.get("vote") or "needs_more_evidence")
            if vote not in {"valid_bug", "false_positive", "needs_more_evidence"}:
                vote = "needs_more_evidence"
            severity = str(parsed.get("severity") or evidence.severity).lower()
            if severity not in {"critical", "high", "medium", "low"}:
                severity = evidence.severity
            return BugValidationResult(
                provider=self.provider_key,
                model=self.model,
                status="completed",
                confidence=float(parsed.get("confidence", 0.0)),
                vote=vote,  # type: ignore[arg-type]
                severity=severity,
                rationale_summary=str(parsed.get("rationale_summary") or ""),
                ai_summary=str(parsed.get("ai_summary") or "")[:2000] or None,
                suggested_fix=str(parsed.get("suggested_fix") or "")[:2000] or None,
                risks=[str(item)[:300] for item in parsed.get("risks", []) if str(item).strip()],
                latency_ms=int((time.perf_counter() - started) * 1000),
            )
        except Exception as exc:
            return BugValidationResult(
                provider=self.provider_key,
                model=self.model,
                status="failed",
                confidence=0.0,
                vote="needs_more_evidence",
                severity=evidence.severity,
                rationale_summary="Gemini did not return a usable bug validation response.",
                error_message=str(exc),
                latency_ms=int((time.perf_counter() - started) * 1000),
            )


async def _post_with_retries(
    client: httpx.AsyncClient,
    url: str,
    payload: dict[str, Any],
    max_retries: int,
) -> httpx.Response:
    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            response = await client.post(url, json=payload)
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
