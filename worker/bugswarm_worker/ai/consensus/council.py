from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from bugswarm_worker.ai.providers.base import ProviderResult


@dataclass(frozen=True)
class ConsensusResult:
    status: str
    confidence: float
    vote_counts: dict[str, int]
    requires_human_review: bool
    final_rationale: str
    accepted_test_cases: list[dict] = field(default_factory=list)
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
