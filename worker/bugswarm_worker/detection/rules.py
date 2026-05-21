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


def detect_console_error(url: str, message: str, source_url: str | None = None) -> DetectedBug | None:
    cleaned = message.strip()
    if not cleaned:
        return None
    affected_url = source_url or url
    return DetectedBug(
        title="Console error detected",
        category="console_error",
        severity="medium",
        affected_url=affected_url,
        expected_result="The page should not emit browser console errors.",
        actual_result=cleaned[:1000],
        fingerprint=fingerprint_bug("console_error", affected_url, cleaned[:300]),
    )


def detect_network_failure(
    request_url: str,
    status_code: int | None,
    failure_text: str | None,
    resource_type: str | None = None,
) -> DetectedBug | None:
    if status_code is not None and status_code < 400:
        return None
    reason = failure_text or (f"HTTP {status_code}" if status_code else "request failed")
    is_document_or_link = resource_type in {None, "document", "fetch", "xhr"}
    category = "broken_link" if status_code == 404 and is_document_or_link else "network_failure"
    severity = "high" if status_code and status_code >= 500 else "medium"
    return DetectedBug(
        title="Broken link detected" if category == "broken_link" else "Network request failure detected",
        category=category,
        severity=severity,
        affected_url=request_url,
        expected_result="Requests made by the page should complete successfully.",
        actual_result=f"{request_url} failed with {reason}.",
        fingerprint=fingerprint_bug(category, request_url, reason),
    )


def detect_navigation_failure(url: str, error_message: str) -> DetectedBug:
    return DetectedBug(
        title="Page navigation failed",
        category="page_navigation_failure",
        severity="high",
        affected_url=url,
        expected_result="The page should load within the configured timeout.",
        actual_result=error_message[:1000],
        fingerprint=fingerprint_bug("page_navigation_failure", url, error_message[:300]),
    )


def detect_infinite_loading(url: str) -> DetectedBug:
    return DetectedBug(
        title="Page did not become idle",
        category="infinite_loading",
        severity="medium",
        affected_url=url,
        expected_result="The page should finish loading network activity in a reasonable time.",
        actual_result="The page did not reach network idle before the configured timeout.",
        fingerprint=fingerprint_bug("infinite_loading", url, "networkidle_timeout"),
    )


def detect_page_crash(url: str, error_message: str | None = None) -> DetectedBug:
    return DetectedBug(
        title="Browser page crashed",
        category="page_crash",
        severity="critical",
        affected_url=url,
        expected_result="The page should remain stable during exploration.",
        actual_result=error_message or "The browser page emitted a crash event.",
        fingerprint=fingerprint_bug("page_crash", url, error_message or "page_crash"),
    )


def detect_element_interaction_failure(url: str, action: str, selector: str | None, error_message: str) -> DetectedBug:
    category = "form_validation_failure" if action in {"ai_fill", "ai_click", "fill", "click"} else "element_interaction_failure"
    return DetectedBug(
        title="Generated form validation failed" if category == "form_validation_failure" else "Element interaction failed",
        category=category,
        severity="medium",
        affected_url=url,
        expected_result="Interactive elements should accept safe generated actions without crashing or timing out.",
        actual_result=error_message[:1000],
        fingerprint=fingerprint_bug(category, url, error_message[:300], selector),
    )
