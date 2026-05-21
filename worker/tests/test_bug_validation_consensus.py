from __future__ import annotations

import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bugswarm_worker.ai.consensus.council import build_bug_validation_consensus
from bugswarm_worker.ai.providers.base import BugValidationResult


class BugValidationConsensusTests(unittest.TestCase):
    def test_valid_majority_updates_severity_and_summary(self) -> None:
        result = build_bug_validation_consensus(
            [
                _result("groq", "valid_bug", "high", 0.9, "Checkout crashes.", "Guard empty carts."),
                _result("gemini", "valid_bug", "high", 0.8, "Crash is reproducible.", "Add empty-cart validation."),
                _result("gptoss", "needs_more_evidence", "medium", 0.3, None, None),
            ],
            "medium",
        )

        self.assertEqual(result.status, "validated")
        self.assertEqual(result.severity, "high")
        self.assertFalse(result.requires_human_review)
        self.assertEqual(result.ai_summary, "Checkout crashes.")

    def test_false_positive_majority_requires_human_review(self) -> None:
        result = build_bug_validation_consensus(
            [
                _result("groq", "false_positive", "low", 0.8, "Expected 404.", None),
                _result("gemini", "false_positive", "low", 0.7, "Route is intentionally missing.", None),
            ],
            "medium",
        )

        self.assertEqual(result.status, "likely_false_positive")
        self.assertEqual(result.severity, "low")
        self.assertTrue(result.requires_human_review)


def _result(provider: str, vote: str, severity: str, confidence: float, summary: str | None, fix: str | None) -> BugValidationResult:
    return BugValidationResult(
        provider=provider,  # type: ignore[arg-type]
        model="test-model",
        status="completed",
        confidence=confidence,
        vote=vote,  # type: ignore[arg-type]
        severity=severity,
        rationale_summary=summary or "No summary.",
        ai_summary=summary,
        suggested_fix=fix,
    )


if __name__ == "__main__":
    unittest.main()
