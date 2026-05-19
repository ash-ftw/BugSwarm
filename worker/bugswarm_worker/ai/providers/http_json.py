from __future__ import annotations

import time
from typing import Any

import httpx

from bugswarm_worker.ai.providers.base import EvidencePacket, ProviderKey, ProviderResult


class OpenAICompatibleJSONProvider:
    def __init__(
        self,
        provider_key: ProviderKey,
        model: str,
        base_url: str,
        api_key: str | None = None,
        timeout_seconds: int = 30,
    ) -> None:
        self.provider_key = provider_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

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
                response = await client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
                response.raise_for_status()
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
- Do not include destructive actions.
- Stay within the configured domain.
- Include concise rationale_summary only, not hidden chain-of-thought.
- Vote approve, reject, or needs_more_evidence.
""".strip()
