from __future__ import annotations

from fnmatch import fnmatch
from urllib.parse import urljoin, urlparse


def normalize_url(base_url: str, candidate_url: str) -> str:
    return urljoin(base_url, candidate_url).split("#", 1)[0]


def is_url_allowed(
    base_url: str,
    candidate_url: str,
    allowed_patterns: list[str] | None = None,
    excluded_patterns: list[str] | None = None,
) -> bool:
    normalized = normalize_url(base_url, candidate_url)
    base = urlparse(base_url)
    candidate = urlparse(normalized)

    if candidate.scheme not in {"http", "https"}:
        return False

    if candidate.netloc != base.netloc:
        return False

    for pattern in excluded_patterns or []:
        if fnmatch(normalized, pattern) or fnmatch(candidate.path, pattern):
            return False

    if not allowed_patterns:
        return True

    return any(fnmatch(normalized, pattern) or fnmatch(candidate.path, pattern) for pattern in allowed_patterns)
