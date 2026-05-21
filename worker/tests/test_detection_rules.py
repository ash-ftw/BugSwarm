from __future__ import annotations

import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bugswarm_worker.detection.rules import (
    detect_blank_page,
    detect_http_error,
    detect_network_failure,
    fingerprint_bug,
)


class DetectionRuleTests(unittest.TestCase):
    def test_http_500_is_high_severity_bug(self) -> None:
        bug = detect_http_error("https://example.com/checkout", 500)
        self.assertIsNotNone(bug)
        assert bug is not None
        self.assertEqual(bug.category, "http_error")
        self.assertEqual(bug.severity, "high")

    def test_blank_page_requires_low_content_and_low_dom_count(self) -> None:
        self.assertIsNone(detect_blank_page("https://example.com", "Loaded", 2))
        bug = detect_blank_page("https://example.com/blank", " ", 3)
        self.assertIsNotNone(bug)
        assert bug is not None
        self.assertEqual(bug.category, "unexpected_blank_page")

    def test_broken_document_link_uses_broken_link_category(self) -> None:
        bug = detect_network_failure("https://example.com/missing", 404, None, "document")
        self.assertIsNotNone(bug)
        assert bug is not None
        self.assertEqual(bug.category, "broken_link")

    def test_fingerprint_is_stable(self) -> None:
        first = fingerprint_bug("console_error", "https://example.com", "Boom", "#root")
        second = fingerprint_bug("console_error", "https://example.com", "Boom", "#root")
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
