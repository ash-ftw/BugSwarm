from __future__ import annotations

import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bugswarm_worker.browser.scope import is_url_allowed, normalize_url


class ScopeTests(unittest.TestCase):
    def test_normalize_url_removes_fragments_and_resolves_relative_links(self) -> None:
        self.assertEqual(
            normalize_url("https://example.com/app/", "../login#top"),
            "https://example.com/login",
        )

    def test_scope_blocks_external_urls(self) -> None:
        self.assertFalse(is_url_allowed("https://example.com", "https://evil.test"))

    def test_scope_honors_allow_and_exclude_patterns(self) -> None:
        self.assertTrue(
            is_url_allowed(
                "https://example.com",
                "https://example.com/shop/products",
                allowed_patterns=["/shop/*"],
                excluded_patterns=["/admin/*"],
            )
        )
        self.assertFalse(
            is_url_allowed(
                "https://example.com",
                "https://example.com/admin/users",
                allowed_patterns=["/*"],
                excluded_patterns=["/admin/*"],
            )
        )


if __name__ == "__main__":
    unittest.main()
