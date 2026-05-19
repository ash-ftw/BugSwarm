from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256


@dataclass(frozen=True)
class DetectedBug:
    title: str
    category: str
    severity: str
    affected_url: str
    actual_result: str
    expected_result: str | None = None
    fingerprint: str | None = None


def fingerprint_bug(category: str, affected_url: str, error_message: str | None, selector: str | None = None) -> str:
    source = "|".join([category, affected_url, error_message or "", selector or ""])
    return sha256(source.encode("utf-8")).hexdigest()


def detect_http_error(url: str, status_code: int) -> DetectedBug | None:
    if status_code < 400:
        return None

    severity = "high" if status_code >= 500 else "medium"
    title = f"HTTP {status_code} response detected"
    return DetectedBug(
        title=title,
        category="http_error",
        severity=severity,
        affected_url=url,
        expected_result="The page should return a successful response.",
        actual_result=f"The page returned HTTP {status_code}.",
        fingerprint=fingerprint_bug("http_error", url, str(status_code)),
    )


def detect_blank_page(url: str, visible_text: str, dom_node_count: int) -> DetectedBug | None:
    if visible_text.strip() or dom_node_count > 8:
        return None

    return DetectedBug(
        title="Unexpected blank page",
        category="unexpected_blank_page",
        severity="high",
        affected_url=url,
        expected_result="The page should render visible content.",
        actual_result="The page rendered almost no visible text or DOM content.",
        fingerprint=fingerprint_bug("unexpected_blank_page", url, "blank"),
    )
