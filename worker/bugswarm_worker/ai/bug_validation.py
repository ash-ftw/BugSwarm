from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from bugswarm_worker.ai.consensus.council import build_bug_validation_consensus
from bugswarm_worker.ai.generation import DEFAULT_PROVIDER_KEYS, _build_provider
from bugswarm_worker.ai.providers.base import BugEvidencePacket, BugValidationResult, ProviderResult
from bugswarm_worker.db import (
    db_connection,
    fetch_bug_validation_evidence,
    fetch_provider_configs,
    insert_model_response,
    insert_reasoning_session,
    update_bug_ai_validation,
)
from bugswarm_worker.events import publish_event


async def validate_bug_with_council(job: dict[str, Any]) -> dict[str, Any]:
    bug_id = str(job["bug_id"])
    provider_keys = [str(provider) for provider in job.get("provider_keys", DEFAULT_PROVIDER_KEYS)]
    consensus_mode = str(job.get("consensus_mode") or "majority_vote")

    with db_connection() as connection:
        raw_evidence = fetch_bug_validation_evidence(connection, bug_id)
    if raw_evidence is None:
        return {"bug_id": bug_id, "status": "not_found"}

    test_run_id = str(raw_evidence["test_run_id"]) if raw_evidence.get("test_run_id") else None
    project_id = str(raw_evidence["project_id"])
    evidence = _evidence_packet(raw_evidence)
    prompt_hash = _prompt_hash(evidence)

    if test_run_id:
        publish_event(
            test_run_id,
            "bug_validation_started",
            {"bug_id": bug_id, "providers": provider_keys, "title": evidence.title},
        )

    provider_results = await _run_validation_providers(project_id, provider_keys or DEFAULT_PROVIDER_KEYS, evidence)
    consensus = build_bug_validation_consensus(provider_results, evidence.severity)

    with db_connection() as connection:
        reasoning_session_id = insert_reasoning_session(
            connection,
            {
                "test_run_id": test_run_id,
                "bug_id": bug_id,
                "task_type": "bug_validation",
                "prompt_fingerprint": prompt_hash,
                "consensus_status": consensus.status,
                "consensus_mode": consensus_mode,
                "final_rationale": consensus.final_rationale,
                "requires_human_review": consensus.requires_human_review,
                "metadata": {
                    "bug_id": bug_id,
                    "vote_counts": consensus.vote_counts,
                    "provider_summaries": consensus.provider_summaries,
                    "previous_severity": evidence.severity,
                    "classified_severity": consensus.severity,
                },
            },
        )
        for result in provider_results:
            insert_model_response(
                connection,
                {
                    "reasoning_session_id": reasoning_session_id,
                    "provider_key": result.provider,
                    "model_name": result.model,
                    "status": result.status,
                    "confidence": result.confidence,
                    "vote": result.vote,
                    "rationale_summary": result.rationale_summary,
                    "output": {
                        "severity": result.severity,
                        "ai_summary": result.ai_summary,
                        "suggested_fix": result.suggested_fix,
                        "risks": result.risks,
                    },
                    "error_message": result.error_message,
                    "latency_ms": result.latency_ms,
                    "token_usage": {},
                },
            )
        update_bug_ai_validation(
            connection,
            bug_id,
            {
                "severity": consensus.severity,
                "ai_summary": consensus.ai_summary or consensus.final_rationale,
                "suggested_fix": consensus.suggested_fix,
                "ai_consensus_status": consensus.status,
                "ai_confidence": consensus.confidence,
                "reasoning_session_id": reasoning_session_id,
            },
        )

    if test_run_id:
        publish_event(
            test_run_id,
            "bug_validation_completed",
            {
                "bug_id": bug_id,
                "status": consensus.status,
                "severity": consensus.severity,
                "confidence": consensus.confidence,
                "requires_human_review": consensus.requires_human_review,
            },
        )

    return {
        "bug_id": bug_id,
        "status": consensus.status,
        "severity": consensus.severity,
        "confidence": consensus.confidence,
        "reasoning_session_id": reasoning_session_id,
    }


async def _run_validation_providers(
    project_id: str,
    provider_keys: list[str],
    evidence: BugEvidencePacket,
) -> list[BugValidationResult]:
    with db_connection() as connection:
        configs = fetch_provider_configs(connection, project_id, provider_keys)
    config_by_key = {config["provider_key"]: config for config in configs}
    results: list[BugValidationResult] = []
    providers = []
    for provider_key in provider_keys:
        provider = _build_provider(provider_key, config_by_key.get(provider_key))
        if isinstance(provider, ProviderResult):
            results.append(_disabled_validation_result(provider, evidence.severity))
        elif provider is not None:
            providers.append(provider)
    if providers:
        results.extend(await asyncio.gather(*(provider.validate_bug(evidence) for provider in providers)))
    return results


def _disabled_validation_result(result: ProviderResult, severity: str) -> BugValidationResult:
    return BugValidationResult(
        provider=result.provider,
        model=result.model,
        status=result.status,
        confidence=0.0,
        vote="needs_more_evidence",
        severity=severity,
        rationale_summary=result.rationale_summary,
        error_message=result.error_message,
        latency_ms=result.latency_ms,
    )


def _evidence_packet(raw: dict[str, Any]) -> BugEvidencePacket:
    return BugEvidencePacket(
        bug_id=str(raw["id"]),
        title=str(raw.get("title") or "Bug"),
        category=str(raw.get("category") or "unknown"),
        severity=str(raw.get("severity") or "medium"),
        affected_url=str(raw.get("affected_url")) if raw.get("affected_url") else None,
        expected_result=str(raw.get("expected_result")) if raw.get("expected_result") else None,
        actual_result=str(raw.get("actual_result")) if raw.get("actual_result") else None,
        replay_steps=_compact(raw.get("replay_steps", []), limit=12),
        artifacts=_compact(raw.get("artifacts", []), limit=10),
        browser_logs=_compact(raw.get("browser_logs", []), limit=12),
        network_logs=_compact(raw.get("network_logs", []), limit=12),
    )


def _compact(items: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    return [_json_safe(item) for item in items[:limit]]


def _prompt_hash(evidence: BugEvidencePacket) -> str:
    return hashlib.sha256(json.dumps(_json_safe(evidence.__dict__), sort_keys=True).encode("utf-8")).hexdigest()


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)
