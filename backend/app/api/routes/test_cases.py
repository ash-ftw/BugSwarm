from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import LLMModelResponse, LLMReasoningSession, Project, TestCase, TestRun, TestStep, User
from app.schemas.test_case import LLMReasoningSessionRead, TestCaseListResponse, TestCaseRead

router = APIRouter()


@router.get("/test-runs/{test_run_id}/test-cases", response_model=TestCaseListResponse)
def list_test_cases(
    test_run_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TestCaseListResponse:
    test_run = _get_owned_test_run(db, test_run_id, current_user.id)
    test_cases = db.scalars(
        select(TestCase)
        .where(TestCase.test_run_id == test_run.id)
        .order_by(TestCase.created_at.desc(), TestCase.name.asc())
    ).all()
    steps_by_case = {
        test_case.id: db.scalars(
            select(TestStep).where(TestStep.test_case_id == test_case.id).order_by(TestStep.step_order.asc())
        ).all()
        for test_case in test_cases
    }
    sessions = db.scalars(
        select(LLMReasoningSession)
        .where(LLMReasoningSession.test_run_id == test_run.id, LLMReasoningSession.task_type == "test_generation")
        .order_by(LLMReasoningSession.created_at.desc())
        .limit(20)
    ).all()
    responses_by_session = {
        session.id: db.scalars(
            select(LLMModelResponse)
            .where(LLMModelResponse.reasoning_session_id == session.id)
            .order_by(LLMModelResponse.provider_key.asc())
        ).all()
        for session in sessions
    }

    return TestCaseListResponse(
        test_cases=[
            TestCaseRead.model_validate({**test_case.__dict__, "steps": steps_by_case[test_case.id]})
            for test_case in test_cases
        ],
        reasoning_sessions=[
            LLMReasoningSessionRead.model_validate(
                {**session.__dict__, "model_responses": responses_by_session[session.id]}
            )
            for session in sessions
        ],
    )


def _get_owned_test_run(db: Session, test_run_id: UUID, user_id: UUID) -> TestRun:
    test_run = db.scalar(
        select(TestRun)
        .join(Project, Project.id == TestRun.project_id)
        .where(TestRun.id == test_run_id, Project.user_id == user_id)
    )
    if test_run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test run was not found.")
    return test_run
