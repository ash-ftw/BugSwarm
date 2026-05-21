from __future__ import annotations

import unittest
from pathlib import Path
import sys

from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.schemas.project import ProjectCreate


class ProjectValidationTests(unittest.TestCase):
    def test_base_url_must_be_http_or_https(self) -> None:
        with self.assertRaises(ValidationError):
            ProjectCreate(
                name="Invalid Target",
                base_url="ftp://example.com",
            )

    def test_base_url_is_trimmed_and_without_trailing_slash(self) -> None:
        payload = ProjectCreate(
            name="Demo Target",
            base_url=" https://example.com/app/ ",
            allowed_paths=[" /shop/* ", ""],
            excluded_paths=[" /admin/* "],
        )
        self.assertEqual(payload.base_url, "https://example.com/app")
        self.assertEqual(payload.allowed_paths, ["/shop/*"])
        self.assertEqual(payload.excluded_paths, ["/admin/*"])


if __name__ == "__main__":
    unittest.main()
