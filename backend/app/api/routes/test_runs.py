from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.queue import celery_app
from app.db.session import get_db
from app.models import (
    Agent,
    AgentStep,
    BrowserLog,
    Bug,
    DiscoveredPage,
    NetworkLog,
    Project,
    ProjectScope,
    TestRun,
    User,
)
from app.schemas.test_run import StartTestRunRequest, StartTestRunResponse, TestRunListResponse, TestRunRead

router = APIRouter()

VIEWPORTS = {
    "desktop": {"width": 1440, "height": 900},
    "tablet": {"width": 900, "height": 1100},
    "mobile": {"width": 390, "height": 844},
}


@router.post("/projects/{project_id}/test-runs", response_model=StartTestRunResponse, status_code=status.HTTP_201_CREATED)
def start_test_run(
    project_id: UUID,
    payload: StartTestRunRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StartTestRunResponse:
    project = _get_owned_project(db, project_id, current_user.id)
    scopes = db.scalars(select(ProjectScope).where(ProjectScope.project_id == project.id)).all()
    allowed_patterns = [scope.pattern for scope in scopes if scope.scope_type == "allow"]
    excluded_patterns = [scope.pattern for scope in scopes if scope.scope_type == "exclude"]

    test_run = TestRun(
        project_id=project.id,
        name=payload.name.strip(),
        status="queued",
        agent_count=payload.agent_count,
        max_depth=payload.max_depth,
        max_duration_minutes=payload.max_duration_minutes,
        test_intensity=payload.test_intensity,
        created_by=current_user.id,
        summary={
            "agent_types": payload.agent_types,
            "viewports": payload.viewports,
            "safe_mode": payload.safe_mode,
            "queue_errors": [],
        },
    )
    db.add(test_run)
    db.flush()

    agents = []
    for index in range(payload.agent_count):
        agent_type = payload.agent_types[index % len(payload.agent_types)]
        viewport_name = payload.viewports[index % len(payload.viewports)]
        viewport = VIEWPORTS[viewport_name]
        agent = Agent(
            test_run_id=test_run.id,
            agent_type=agent_type,
            status="queued",
            viewport_width=viewport["width"],
            viewport_height=viewport["height"],
        )
        db.add(agent)
        agents.append((agent, viewport_name, viewport))

    db.commit()
    db.refresh(test_run)
    for agent, viewport_name, viewport in agents:
        db.refresh(agent)
        job = {
            "project_id": str(project.id),
            "test_run_id": str(test_run.id),
            "agent_id": str(agent.id),
            "base_url": project.base_url,
            "agent_type": agent.agent_type,
            "max_depth": payload.max_depth,
            "max_duration_minutes": payload.max_duration_minutes,
            "viewport": viewport,
            "viewport_name": viewport_name,
            "allowed_patterns": allowed_patterns,
            "excluded_patterns": excluded_patterns,
            "safe_mode": payload.safe_mode,
        }
        try:
            celery_app.send_task("bugswarm.run_agent", args=[job])
        except Exception as exc:
            _mark_queue_error(db, test_run.id, agent.id, str(exc))

    return StartTestRunResponse(test_run_id=test_run.id, status=test_run.status)


@router.get("/projects/{project_id}/test-runs", response_model=TestRunListResponse)
def list_test_runs(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TestRunListResponse:
    project = _get_owned_project(db, project_id, current_user.id)
    test_runs = db.scalars(
        select(TestRun).where(TestRun.project_id == project.id).order_by(TestRun.created_at.desc())
    ).all()
    return TestRunListResponse(test_runs=[_read_test_run(db, test_run) for test_run in test_runs])


@router.get("/test-runs/{test_run_id}", response_model=TestRunRead)
def get_test_run(
    test_run_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TestRunRead:
    test_run = _get_owned_test_run(db, test_run_id, current_user.id)
    return _read_test_run(db, test_run)


@router.post("/test-runs/{test_run_id}/stop", response_model=TestRunRead)
def stop_test_run(
    test_run_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TestRunRead:
    test_run = _get_owned_test_run(db, test_run_id, current_user.id)
    if test_run.status in {"completed", "failed", "cancelled"}:
        return _read_test_run(db, test_run)

    test_run.status = "cancelled"
    test_run.completed_at = datetime.utcnow()
    agents = db.scalars(select(Agent).where(Agent.test_run_id == test_run.id)).all()
    for agent in agents:
        if agent.status in {"queued", "running"}:
            agent.status = "cancelled"
            agent.completed_at = datetime.utcnow()
    db.commit()
    db.refresh(test_run)
    return _read_test_run(db, test_run)


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


def _read_test_run(db: Session, test_run: TestRun) -> TestRunRead:
    agents = db.scalars(select(Agent).where(Agent.test_run_id == test_run.id).order_by(Agent.created_at.asc())).all()
    discovered_pages = db.scalars(
        select(DiscoveredPage)
        .where(DiscoveredPage.test_run_id == test_run.id)
        .order_by(DiscoveredPage.last_seen_at.desc())
        .limit(20)
    ).all()
    return TestRunRead.model_validate(
        {
            **test_run.__dict__,
            "agents": agents,
            "discovered_pages": discovered_pages,
            "discovered_pages_count": _count(db, DiscoveredPage, DiscoveredPage.test_run_id == test_run.id),
            "agent_steps_count": _count(db, AgentStep, AgentStep.agent_id.in_([agent.id for agent in agents])) if agents else 0,
            "browser_logs_count": _count(db, BrowserLog, BrowserLog.test_run_id == test_run.id),
            "network_logs_count": _count(db, NetworkLog, NetworkLog.test_run_id == test_run.id),
            "bugs_count": _count(db, Bug, Bug.test_run_id == test_run.id),
        }
    )


def _count(db: Session, model: type, where_clause) -> int:
    return int(db.scalar(select(func.count()).select_from(model).where(where_clause)) or 0)


def _mark_queue_error(db: Session, test_run_id: UUID, agent_id: UUID, error_message: str) -> None:
    test_run = db.get(TestRun, test_run_id)
    agent = db.get(Agent, agent_id)
    if test_run is not None:
        summary = dict(test_run.summary or {})
        queue_errors = list(summary.get("queue_errors", []))
        queue_errors.append({"agent_id": str(agent_id), "message": error_message})
        summary["queue_errors"] = queue_errors
        test_run.summary = summary
        test_run.status = "failed"
    if agent is not None:
        agent.status = "failed"
        agent.error_message = error_message
        agent.completed_at = datetime.utcnow()
    db.commit()
