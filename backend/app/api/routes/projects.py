from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models import LLMProviderConfig, Project, ProjectScope, User
from app.schemas.project import ProjectCreate, ProjectListResponse, ProjectRead, ProjectUpdate

router = APIRouter()


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectRead:
    project = Project(
        user_id=current_user.id,
        name=payload.name.strip(),
        description=payload.description,
        base_url=payload.base_url,
        default_max_depth=payload.default_max_depth,
        default_agent_count=payload.default_agent_count,
        default_test_intensity=payload.default_test_intensity,
        llm_council_enabled=payload.llm_council_enabled,
        llm_consensus_mode=payload.llm_consensus_mode,
        free_ai_mode=payload.free_ai_mode,
    )
    db.add(project)
    db.flush()

    _replace_project_scopes(db, project.id, payload.allowed_paths, payload.excluded_paths)
    _create_default_provider_configs(db, project.id)
    db.commit()
    db.refresh(project)

    return _read_project(db, project)


@router.get("", response_model=ProjectListResponse)
def list_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectListResponse:
    projects = db.scalars(
        select(Project).where(Project.user_id == current_user.id).order_by(Project.created_at.desc())
    ).all()
    return ProjectListResponse(projects=[_read_project(db, project) for project in projects])


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectRead:
    project = _get_owned_project(db, project_id, current_user.id)
    return _read_project(db, project)


@router.patch("/{project_id}", response_model=ProjectRead)
def update_project(
    project_id: UUID,
    payload: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectRead:
    project = _get_owned_project(db, project_id, current_user.id)
    update_data = payload.model_dump(exclude_unset=True, exclude={"allowed_paths", "excluded_paths"})

    for field_name, value in update_data.items():
        setattr(project, field_name, value)

    if "allowed_paths" in payload.model_fields_set or "excluded_paths" in payload.model_fields_set:
        current_scopes = db.scalars(select(ProjectScope).where(ProjectScope.project_id == project.id)).all()
        current_allowed = [scope.pattern for scope in current_scopes if scope.scope_type == "allow"]
        current_excluded = [scope.pattern for scope in current_scopes if scope.scope_type == "exclude"]
        _replace_project_scopes(
            db,
            project.id,
            payload.allowed_paths if payload.allowed_paths is not None else current_allowed,
            payload.excluded_paths if payload.excluded_paths is not None else current_excluded,
        )

    project.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(project)
    return _read_project(db, project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_project(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    project = _get_owned_project(db, project_id, current_user.id)
    db.delete(project)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _get_owned_project(db: Session, project_id: UUID, user_id: UUID) -> Project:
    project = db.scalar(select(Project).where(Project.id == project_id, Project.user_id == user_id))
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project was not found.")
    return project


def _read_project(db: Session, project: Project) -> ProjectRead:
    scopes = db.scalars(
        select(ProjectScope).where(ProjectScope.project_id == project.id).order_by(ProjectScope.created_at.asc())
    ).all()
    provider_configs = db.scalars(
        select(LLMProviderConfig)
        .where(LLMProviderConfig.project_id == project.id)
        .order_by(LLMProviderConfig.provider_key.asc())
    ).all()
    return ProjectRead.model_validate(
        {
            **project.__dict__,
            "scopes": scopes,
            "llm_provider_configs": provider_configs,
        }
    )


def _replace_project_scopes(
    db: Session,
    project_id: UUID,
    allowed_paths: list[str],
    excluded_paths: list[str],
) -> None:
    db.execute(delete(ProjectScope).where(ProjectScope.project_id == project_id))
    for pattern in allowed_paths:
        db.add(ProjectScope(project_id=project_id, scope_type="allow", pattern=pattern))
    for pattern in excluded_paths:
        db.add(ProjectScope(project_id=project_id, scope_type="exclude", pattern=pattern))


def _create_default_provider_configs(db: Session, project_id: UUID) -> None:
    configs = [
        LLMProviderConfig(
            project_id=project_id,
            provider_key="groq",
            model_name=settings.groq_model,
            base_url=None,
            is_enabled=bool(settings.groq_api_key),
            is_free_mode=settings.ai_free_mode,
        ),
        LLMProviderConfig(
            project_id=project_id,
            provider_key="gptoss",
            model_name=settings.gptoss_model,
            base_url=settings.gptoss_base_url,
            is_enabled=bool(settings.gptoss_base_url),
            is_free_mode=True,
        ),
        LLMProviderConfig(
            project_id=project_id,
            provider_key="openrouter",
            model_name=settings.openrouter_model,
            base_url=settings.openrouter_base_url,
            is_enabled=bool(settings.openrouter_api_key),
            is_free_mode=settings.ai_free_mode,
        ),
        LLMProviderConfig(
            project_id=project_id,
            provider_key="gemini",
            model_name=settings.gemini_model,
            base_url=None,
            is_enabled=bool(settings.gemini_api_key),
            is_free_mode=settings.ai_free_mode,
        ),
    ]
    db.add_all(configs)
