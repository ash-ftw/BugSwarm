from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select

from app.core.events import subscribe_test_run_events
from app.core.security import decode_access_token
from app.db.session import SessionLocal
from app.models import Agent, Project, TestRun, User

router = APIRouter()


@router.websocket("/ws/test-runs/{test_run_id}")
async def test_run_events(websocket: WebSocket, test_run_id: UUID) -> None:
    user_id = _authenticate_socket(websocket)
    if user_id is None or not _user_owns_test_run(test_run_id, user_id):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    await websocket.send_json(_snapshot_event(test_run_id))

    try:
        async for event in subscribe_test_run_events(test_run_id):
            await websocket.send_json(event)
    except WebSocketDisconnect:
        return


def _authenticate_socket(websocket: WebSocket) -> UUID | None:
    token = websocket.query_params.get("token")
    if not token:
        return None
    subject = decode_access_token(token)
    if subject is None:
        return None
    try:
        return UUID(subject)
    except ValueError:
        return None


def _user_owns_test_run(test_run_id: UUID, user_id: UUID) -> bool:
    with SessionLocal() as db:
        return (
            db.scalar(
                select(TestRun.id)
                .join(Project, Project.id == TestRun.project_id)
                .join(User, User.id == Project.user_id)
                .where(TestRun.id == test_run_id, User.id == user_id)
            )
            is not None
        )


def _snapshot_event(test_run_id: UUID) -> dict:
    with SessionLocal() as db:
        test_run = db.get(TestRun, test_run_id)
        agents = db.scalars(select(Agent).where(Agent.test_run_id == test_run_id)).all()
        return {
            "event": "snapshot",
            "test_run_id": str(test_run_id),
            "status": test_run.status if test_run else "unknown",
            "agents": [
                {
                    "agent_id": str(agent.id),
                    "agent_type": agent.agent_type,
                    "status": agent.status,
                    "current_url": agent.current_url,
                }
                for agent in agents
            ],
        }
