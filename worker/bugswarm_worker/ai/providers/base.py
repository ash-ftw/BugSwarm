from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

ProviderKey = Literal["groq", "gptoss", "gemini"]
ProviderVote = Literal["approve", "reject", "needs_more_evidence"]


@dataclass(frozen=True)
class EvidencePacket:
    url: str
    title: str | None = None
    forms: list[dict[str, Any]] = field(default_factory=list)
    buttons: list[dict[str, Any]] = field(default_factory=list)
    links: list[dict[str, Any]] = field(default_factory=list)
    inputs: list[dict[str, Any]] = field(default_factory=list)
    console_errors: list[str] = field(default_factory=list)
    network_failures: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class ProviderResult:
    provider: ProviderKey
    model: str
    status: str
    confidence: float
    vote: ProviderVote
    rationale_summary: str
    risks: list[str] = field(default_factory=list)
    test_cases: list[dict[str, Any]] = field(default_factory=list)
    error_message: str | None = None
    latency_ms: int | None = None


class LLMProvider(Protocol):
    provider_key: ProviderKey

    async def generate_tests(self, evidence: EvidencePacket) -> ProviderResult:
        ...
