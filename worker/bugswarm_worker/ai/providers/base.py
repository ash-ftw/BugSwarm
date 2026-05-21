from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

ProviderKey = Literal["groq", "gptoss", "gemini", "openrouter"]
ProviderVote = Literal["approve", "reject", "needs_more_evidence", "valid_bug", "false_positive"]


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
class BugEvidencePacket:
    bug_id: str
    title: str
    category: str
    severity: str
    affected_url: str | None
    expected_result: str | None = None
    actual_result: str | None = None
    replay_steps: list[dict[str, Any]] = field(default_factory=list)
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    browser_logs: list[dict[str, Any]] = field(default_factory=list)
    network_logs: list[dict[str, Any]] = field(default_factory=list)


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


@dataclass(frozen=True)
class BugValidationResult:
    provider: ProviderKey
    model: str
    status: str
    confidence: float
    vote: ProviderVote
    severity: str
    rationale_summary: str
    ai_summary: str | None = None
    suggested_fix: str | None = None
    risks: list[str] = field(default_factory=list)
    error_message: str | None = None
    latency_ms: int | None = None


class LLMProvider(Protocol):
    provider_key: ProviderKey

    async def generate_tests(self, evidence: EvidencePacket) -> ProviderResult:
        ...

    async def validate_bug(self, evidence: BugEvidencePacket) -> BugValidationResult:
        ...
