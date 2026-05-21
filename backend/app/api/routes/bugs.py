from __future__ import annotations

from pathlib import Path
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.queue import celery_app
from app.db.session import get_db
from app.models import (
    BrowserLog,
    Bug,
    BugArtifact,
    LLMModelResponse,
    LLMReasoningSession,
    NetworkLog,
    Project,
    ReplayStep,
    Report,
    TestRun,
    User,
)
from app.schemas.bug import (
    BugListResponse,
    BugRead,
    BugUpdate,
    BugValidationHistoryResponse,
    BugValidationResponse,
    PlaywrightScriptResponse,
    ReplayHistoryResponse,
    ReplayResponse,
)

router = APIRouter()


@router.get("/projects/{project_id}/bugs", response_model=BugListResponse)
def list_project_bugs(
    project_id: UUID,
    severity: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    test_run_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BugListResponse:
    _get_owned_project(db, project_id, current_user.id)
    query = select(Bug).where(Bug.project_id == project_id)
    if severity:
        query = query.where(Bug.severity == severity)
    if status_filter:
        query = query.where(Bug.status == status_filter)
    if test_run_id:
        query = query.where(Bug.test_run_id == test_run_id)
    bugs = db.scalars(query.order_by(Bug.last_seen_at.desc(), Bug.created_at.desc()).limit(200)).all()
    return BugListResponse(bugs=[_read_bug(db, bug) for bug in bugs])


@router.get("/bugs/{bug_id}", response_model=BugRead)
def get_bug(
    bug_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BugRead:
    bug = _get_owned_bug(db, bug_id, current_user.id)
    return _read_bug(db, bug)


@router.patch("/bugs/{bug_id}", response_model=BugRead)
def update_bug(
    bug_id: UUID,
    payload: BugUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BugRead:
    bug = _get_owned_bug(db, bug_id, current_user.id)
    update_data = payload.model_dump(exclude_unset=True)
    for field_name, value in update_data.items():
        setattr(bug, field_name, value)
    db.commit()
    db.refresh(bug)
    return _read_bug(db, bug)


@router.get("/bugs/{bug_id}/validation", response_model=BugValidationHistoryResponse)
def get_bug_validation(
    bug_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BugValidationHistoryResponse:
    bug = _get_owned_bug(db, bug_id, current_user.id)
    sessions = db.scalars(
        select(LLMReasoningSession)
        .where(LLMReasoningSession.bug_id == bug.id, LLMReasoningSession.task_type == "bug_validation")
        .order_by(LLMReasoningSession.created_at.desc())
        .limit(20)
    ).all()
    payload = []
    for session in sessions:
        responses = db.scalars(
            select(LLMModelResponse)
            .where(LLMModelResponse.reasoning_session_id == session.id)
            .order_by(LLMModelResponse.provider_key.asc())
        ).all()
        payload.append(
            {
                "id": str(session.id),
                "test_run_id": str(session.test_run_id) if session.test_run_id else None,
                "bug_id": str(session.bug_id) if session.bug_id else None,
                "task_type": session.task_type,
                "prompt_fingerprint": session.prompt_fingerprint,
                "consensus_status": session.consensus_status,
                "consensus_mode": session.consensus_mode,
                "final_rationale": session.final_rationale,
                "requires_human_review": session.requires_human_review,
                "metadata": session.session_metadata,
                "created_at": session.created_at.isoformat(),
                "model_responses": [
                    {
                        "id": str(response.id),
                        "provider_key": response.provider_key,
                        "model_name": response.model_name,
                        "status": response.status,
                        "confidence": float(response.confidence) if response.confidence is not None else None,
                        "vote": response.vote,
                        "rationale_summary": response.rationale_summary,
                        "output": response.output,
                        "error_message": response.error_message,
                        "latency_ms": response.latency_ms,
                        "created_at": response.created_at.isoformat(),
                    }
                    for response in responses
                ],
            }
        )
    return BugValidationHistoryResponse(bug_id=bug.id, sessions=payload)


@router.post("/bugs/{bug_id}/validate", response_model=BugValidationResponse)
def validate_bug(
    bug_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BugValidationResponse:
    bug = _get_owned_bug(db, bug_id, current_user.id)
    project = db.get(Project, bug.project_id)
    provider_keys = ["groq", "gptoss", "gemini", "openrouter"]
    result = celery_app.send_task(
        "bugswarm.validate_bug",
        args=[
            {
                "bug_id": str(bug.id),
                "provider_keys": provider_keys,
                "consensus_mode": project.llm_consensus_mode if project else "majority_vote",
            }
        ],
    )
    return BugValidationResponse(bug_id=bug.id, status="queued", task_id=result.id)


@router.get("/bugs/{bug_id}/replay", response_model=ReplayHistoryResponse)
def get_bug_replay(
    bug_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReplayHistoryResponse:
    bug = _get_owned_bug(db, bug_id, current_user.id)
    replay_steps = db.scalars(select(ReplayStep).where(ReplayStep.bug_id == bug.id).order_by(ReplayStep.step_order.asc())).all()
    attempts = _replay_attempts(db, bug)
    return ReplayHistoryResponse(bug_id=bug.id, replay_steps=replay_steps, attempts=attempts)


@router.post("/bugs/{bug_id}/replay", response_model=ReplayResponse)
def replay_bug(
    bug_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReplayResponse:
    bug = _get_owned_bug(db, bug_id, current_user.id)
    if not bug.test_run_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Bug is not associated with a test run.")
    result = celery_app.send_task("bugswarm.replay_bug", args=[{"bug_id": str(bug.id)}])
    return ReplayResponse(bug_id=bug.id, status="queued", task_id=result.id)


@router.get("/bugs/{bug_id}/playwright-script", response_model=PlaywrightScriptResponse)
def get_playwright_script(
    bug_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PlaywrightScriptResponse:
    bug = _get_owned_bug(db, bug_id, current_user.id)
    replay_steps = db.scalars(select(ReplayStep).where(ReplayStep.bug_id == bug.id).order_by(ReplayStep.step_order.asc())).all()
    script = _playwright_script(bug, replay_steps)
    if bug.test_run_id:
        db.add(
            Report(
                test_run_id=bug.test_run_id,
                report_type="playwright_script",
                file_path=None,
                content={"bug_id": str(bug.id), "script": script},
            )
        )
        db.commit()
    return PlaywrightScriptResponse(bug_id=bug.id, script=script)


@router.get("/bug-artifacts/{artifact_id}")
def get_bug_artifact(
    artifact_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    artifact = db.get(BugArtifact, artifact_id)
    if artifact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact was not found.")
    _get_owned_bug(db, artifact.bug_id, current_user.id)
    path = Path(artifact.file_path)
    if not path.exists() and not path.is_absolute():
        path = Path(settings.artifact_storage_root) / path
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact file was not found.")
    return FileResponse(path, media_type=artifact.mime_type, filename=path.name)


@router.get("/test-runs/{test_run_id}/report")
def get_test_run_report(
    test_run_id: UUID,
    format: Literal["json", "markdown"] = "json",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    test_run = _get_owned_test_run(db, test_run_id, current_user.id)
    bugs = db.scalars(select(Bug).where(Bug.test_run_id == test_run.id).order_by(Bug.severity.asc())).all()
    content = _report_content(test_run, bugs)
    report = Report(test_run_id=test_run.id, report_type=format, file_path=None, content=content)
    db.add(report)
    db.commit()
    if format == "markdown":
        return PlainTextResponse(_report_markdown(content), media_type="text/markdown")
    return JSONResponse(content)


def _get_owned_project(db: Session, project_id: UUID, user_id: UUID) -> Project:
    project = db.scalar(select(Project).where(Project.id == project_id, Project.user_id == user_id))
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project was not found.")
    return project


def _get_owned_test_run(db: Session, test_run_id: UUID, user_id: UUID) -> TestRun:
    test_run = db.scalar(
        select(TestRun)
        .join(Project, Project.id == TestRun.project_id)
        .where(TestRun.id == test_run_id, Project.user_id == user_id)
    )
    if test_run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test run was not found.")
    return test_run


def _get_owned_bug(db: Session, bug_id: UUID, user_id: UUID) -> Bug:
    bug = db.scalar(
        select(Bug)
        .join(Project, Project.id == Bug.project_id)
        .where(Bug.id == bug_id, Project.user_id == user_id)
    )
    if bug is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bug was not found.")
    return bug


def _read_bug(db: Session, bug: Bug) -> BugRead:
    artifacts = db.scalars(select(BugArtifact).where(BugArtifact.bug_id == bug.id).order_by(BugArtifact.created_at.asc())).all()
    replay_steps = db.scalars(select(ReplayStep).where(ReplayStep.bug_id == bug.id).order_by(ReplayStep.step_order.asc())).all()
    browser_logs = db.scalars(
        select(BrowserLog)
        .where(BrowserLog.test_run_id == bug.test_run_id, BrowserLog.source_url == bug.affected_url)
        .order_by(BrowserLog.created_at.desc())
        .limit(10)
    ).all()
    network_logs = db.scalars(
        select(NetworkLog)
        .where(NetworkLog.test_run_id == bug.test_run_id, NetworkLog.request_url == bug.affected_url)
        .order_by(NetworkLog.created_at.desc())
        .limit(10)
    ).all()
    return BugRead.model_validate(
        {
            **bug.__dict__,
            "artifacts": artifacts,
            "replay_steps": replay_steps,
            "browser_logs": browser_logs,
            "network_logs": network_logs,
        }
    )


def _replay_attempts(db: Session, bug: Bug) -> list[dict]:
    if bug.test_run_id is None:
        return []
    reports = db.scalars(
        select(Report)
        .where(Report.test_run_id == bug.test_run_id, Report.report_type == "replay_attempt")
        .order_by(Report.generated_at.desc())
        .limit(25)
    ).all()
    attempts = []
    for report in reports:
        content = report.content or {}
        if content.get("bug_id") == str(bug.id):
            attempts.append({**content, "report_id": str(report.id), "generated_at": report.generated_at.isoformat()})
    return attempts


def _report_content(test_run: TestRun, bugs: list[Bug]) -> dict:
    severity_counts: dict[str, int] = {}
    status_counts: dict[str, int] = {}
    for bug in bugs:
        severity_counts[bug.severity] = severity_counts.get(bug.severity, 0) + 1
        status_counts[bug.status] = status_counts.get(bug.status, 0) + 1
    return {
        "test_run": {
            "id": str(test_run.id),
            "project_id": str(test_run.project_id),
            "name": test_run.name,
            "status": test_run.status,
            "created_at": test_run.created_at.isoformat(),
            "completed_at": test_run.completed_at.isoformat() if test_run.completed_at else None,
        },
        "summary": {
            "bug_count": len(bugs),
            "severity_counts": severity_counts,
            "status_counts": status_counts,
        },
        "bugs": [
            {
                "id": str(bug.id),
                "title": bug.title,
                "category": bug.category,
                "severity": bug.severity,
                "status": bug.status,
                "affected_url": bug.affected_url,
                "expected_result": bug.expected_result,
                "actual_result": bug.actual_result,
                "fingerprint": bug.fingerprint,
            }
            for bug in bugs
        ],
    }


def _report_markdown(content: dict) -> str:
    lines = [
        f"# BugSwarm Report: {content['test_run']['name']}",
        "",
        f"- Status: {content['test_run']['status']}",
        f"- Bugs: {content['summary']['bug_count']}",
        "",
        "## Findings",
    ]
    for bug in content["bugs"]:
        lines.extend(
            [
                "",
                f"### {bug['severity'].title()} - {bug['title']}",
                f"- Category: {bug['category']}",
                f"- Status: {bug['status']}",
                f"- URL: {bug['affected_url']}",
                f"- Expected: {bug['expected_result'] or 'Not recorded'}",
                f"- Actual: {bug['actual_result'] or 'Not recorded'}",
            ]
        )
    return "\n".join(lines) + "\n"


def _playwright_script(bug: Bug, replay_steps: list[ReplayStep]) -> str:
    title = _quote(bug.title)
    steps = replay_steps or [ReplayStep(bug_id=bug.id, step_order=1, action_type="goto", url=bug.affected_url)]
    lines = [
        "import { test, expect } from '@playwright/test';",
        "",
        f"test('Replay: {title}', async ({{ page }}) => {{",
    ]
    for step in steps:
        lines.extend(_script_lines_for_step(step, bug))
    if bug.expected_result:
        lines.append(f"  // Expected: {_comment(bug.expected_result)}")
    if bug.actual_result:
        lines.append(f"  // Observed failure: {_comment(bug.actual_result)}")
    lines.append("});")
    return "\n".join(lines) + "\n"


def _script_lines_for_step(step: ReplayStep, bug: Bug) -> list[str]:
    action = (step.action_type or "goto").replace("ai_", "")
    selector = step.selector or step.selector_hint
    url = step.url or bug.affected_url
    if action in {"goto", "navigation"}:
        return [f"  await page.goto('{_quote(str(url or ''))}');"]
    if action in {"fill", "input"}:
        return [f"  await {_locator_script(selector)}.fill('{_quote(str(step.input_value or ''))}');"]
    if action in {"click", "button"}:
        return [f"  await {_locator_script(selector)}.click();"]
    if action == "assert_text":
        text = step.expected_result or selector or ""
        return [f"  await expect(page.getByText('{_quote(str(text))}')).toBeVisible();"]
    return [f"  // Unsupported replay action: {_comment(action)}"]


def _locator_script(selector: str | None) -> str:
    if selector and _looks_like_css(selector):
        return f"page.locator('{_quote(selector)}')"
    if selector:
        return f"page.getByText('{_quote(selector)}')"
    return "page.locator('button, input, textarea, select, a').first()"


def _looks_like_css(value: str) -> bool:
    lowered = value.strip().lower()
    return lowered.startswith(("#", ".", "[", "input", "textarea", "select", "button", "a[", "form"))


def _quote(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")


def _comment(value: str) -> str:
    return " ".join(value.split())[:500]
