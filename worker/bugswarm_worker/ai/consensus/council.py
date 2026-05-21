from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from bugswarm_worker.ai.providers.base import BugValidationResult, ProviderResult


@dataclass(frozen=True)
class ConsensusResult:
    status: str
    confidence: float
    vote_counts: dict[str, int]
    requires_human_review: bool
    final_rationale: str
    accepted_test_cases: list[dict] = field(default_factory=list)
    provider_summaries: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class BugValidationConsensus:
    status: str
    confidence: float
    vote_counts: dict[str, int]
    severity: str
    requires_human_review: bool
    final_rationale: str
    ai_summary: str | None = None
    suggested_fix: str | None = None
    provider_summaries: list[str] = field(default_factory=list)


def build_consensus(results: list[ProviderResult]) -> ConsensusResult:
    completed = [result for result in results if result.status == "completed"]
    vote_counts = Counter(result.vote for result in results)
    provider_summaries = [
        f"{result.provider}: {result.vote} ({result.confidence:.2f}) - {result.rationale_summary}"
        for result in results
    ]

    if not completed:
        return ConsensusResult(
            status="degraded_no_provider",
            confidence=0.0,
            vote_counts=dict(vote_counts),
            requires_human_review=True,
            final_rationale="No reasoning provider returned a completed response.",
            provider_summaries=provider_summaries,
        )

    if vote_counts.get("reject", 0) > 0:
        return ConsensusResult(
            status="blocked_by_provider",
            confidence=min(result.confidence for result in completed),
            vote_counts=dict(vote_counts),
            requires_human_review=True,
            final_rationale="At least one provider rejected the proposed action, so safe mode requires review.",
            provider_summaries=provider_summaries,
        )

    approvals = [result for result in completed if result.vote == "approve"]
    if len(approvals) >= 2:
        accepted = []
        for result in approvals:
            accepted.extend(result.test_cases)
        confidence = sum(result.confidence for result in approvals) / len(approvals)
        return ConsensusResult(
            status="approved",
            confidence=confidence,
            vote_counts=dict(vote_counts),
            requires_human_review=False,
            final_rationale="At least two providers approved safe test generation.",
            accepted_test_cases=accepted,
            provider_summaries=provider_summaries,
        )

    confidence = sum(result.confidence for result in completed) / len(completed)
    return ConsensusResult(
        status="needs_more_evidence",
        confidence=confidence,
        vote_counts=dict(vote_counts),
        requires_human_review=True,
        final_rationale="The council did not reach a majority approval.",
        provider_summaries=provider_summaries,
    )


def build_bug_validation_consensus(
    results: list[BugValidationResult],
    original_severity: str,
) -> BugValidationConsensus:
    completed = [result for result in results if result.status == "completed"]
    vote_counts = Counter(result.vote for result in results)
    provider_summaries = [
        f"{result.provider}: {result.vote} ({result.confidence:.2f}, {result.severity}) - {result.rationale_summary}"
        for result in results
    ]

    if not completed:
        return BugValidationConsensus(
            status="degraded_no_provider",
            confidence=0.0,
            vote_counts=dict(vote_counts),
            severity=original_severity,
            requires_human_review=True,
            final_rationale="No reasoning provider returned a completed validation response.",
            provider_summaries=provider_summaries,
        )

    valid_votes = [result for result in completed if result.vote == "valid_bug"]
    false_positive_votes = [result for result in completed if result.vote == "false_positive"]
    if len(false_positive_votes) >= 2:
        confidence = _average_confidence(false_positive_votes)
        return BugValidationConsensus(
            status="likely_false_positive",
            confidence=confidence,
            vote_counts=dict(vote_counts),
            severity="low",
            requires_human_review=True,
            final_rationale="At least two providers judged the finding likely to be a false positive.",
            ai_summary=_best_text(false_positive_votes, "ai_summary"),
            suggested_fix=_best_text(false_positive_votes, "suggested_fix"),
            provider_summaries=provider_summaries,
        )

    if len(valid_votes) >= 2:
        confidence = _average_confidence(valid_votes)
        severity = _weighted_severity(valid_votes, original_severity)
        return BugValidationConsensus(
            status="validated",
            confidence=confidence,
            vote_counts=dict(vote_counts),
            severity=severity,
            requires_human_review=False,
            final_rationale="At least two providers validated this finding as a product bug.",
            ai_summary=_best_text(valid_votes, "ai_summary"),
            suggested_fix=_best_text(valid_votes, "suggested_fix"),
            provider_summaries=provider_summaries,
        )

    confidence = _average_confidence(completed)
    return BugValidationConsensus(
        status="needs_more_evidence",
        confidence=confidence,
        vote_counts=dict(vote_counts),
        severity=_weighted_severity(completed, original_severity),
        requires_human_review=True,
        final_rationale="The council did not reach a majority validation decision.",
        ai_summary=_best_text(completed, "ai_summary"),
        suggested_fix=_best_text(completed, "suggested_fix"),
        provider_summaries=provider_summaries,
    )


def _average_confidence(results: list[BugValidationResult]) -> float:
    return sum(result.confidence for result in results) / len(results) if results else 0.0


def _weighted_severity(results: list[BugValidationResult], fallback: str) -> str:
    scores = {"low": 1, "medium": 2, "high": 3, "critical": 4}
    weighted: dict[str, float] = {}
    for result in results:
        severity = result.severity if result.severity in scores else fallback
        weighted[severity] = weighted.get(severity, 0.0) + max(result.confidence, 0.1) * scores.get(severity, 2)
    if not weighted:
        return fallback
    return max(weighted.items(), key=lambda item: item[1])[0]


def _best_text(results: list[BugValidationResult], field_name: str) -> str | None:
    ordered = sorted(results, key=lambda result: result.confidence, reverse=True)
    for result in ordered:
        value = getattr(result, field_name)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None
