from __future__ import annotations

from urllib.parse import urlparse
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.security import encrypt_secret
from app.db.session import get_db
from app.models import AuthProfile, Project, User
from app.schemas.auth_profile import (
    AuthProfileCreate,
    AuthProfileListResponse,
    AuthProfileRead,
    AuthProfileUpdate,
)

router = APIRouter()


@router.get("/projects/{project_id}/auth-profiles", response_model=AuthProfileListResponse)
def list_auth_profiles(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AuthProfileListResponse:
    project = _get_owned_project(db, project_id, current_user.id)
    profiles = db.scalars(
        select(AuthProfile).where(AuthProfile.project_id == project.id).order_by(AuthProfile.created_at.asc())
    ).all()
    return AuthProfileListResponse(auth_profiles=[_read_profile(profile) for profile in profiles])


@router.post("/projects/{project_id}/auth-profiles", response_model=AuthProfileRead, status_code=status.HTTP_201_CREATED)
def create_auth_profile(
    project_id: UUID,
    payload: AuthProfileCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AuthProfileRead:
    project = _get_owned_project(db, project_id, current_user.id)
    _validate_profile_against_project(project, payload.auth_type, payload.login_url, payload.storage_state_path)
    profile = AuthProfile(
        project_id=project.id,
        name=payload.name.strip(),
        auth_type=payload.auth_type,
        login_url=payload.login_url,
        username_selector=payload.username_selector,
        password_selector=payload.password_selector,
        submit_selector=payload.submit_selector,
        username_value=payload.username_value,
        encrypted_password_value=encrypt_secret(payload.password_value),
        storage_state_path=payload.storage_state_path,
        is_active=payload.is_active,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return _read_profile(profile)


@router.patch("/auth-profiles/{profile_id}", response_model=AuthProfileRead)
def update_auth_profile(
    profile_id: UUID,
    payload: AuthProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AuthProfileRead:
    profile = _get_owned_profile(db, profile_id, current_user.id)
    project = db.get(Project, profile.project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project was not found.")

    update_data = payload.model_dump(exclude_unset=True, exclude={"password_value"})
    next_auth_type = update_data.get("auth_type", profile.auth_type)
    next_login_url = update_data.get("login_url", profile.login_url)
    next_storage_state_path = update_data.get("storage_state_path", profile.storage_state_path)
    _validate_profile_against_project(project, next_auth_type, next_login_url, next_storage_state_path)

    for field_name, value in update_data.items():
        setattr(profile, field_name, value.strip() if isinstance(value, str) else value)
    if "password_value" in payload.model_fields_set:
        profile.encrypted_password_value = encrypt_secret(payload.password_value)
    db.commit()
    db.refresh(profile)
    return _read_profile(profile)


@router.delete("/auth-profiles/{profile_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_auth_profile(
    profile_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    profile = _get_owned_profile(db, profile_id, current_user.id)
    db.delete(profile)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _get_owned_project(db: Session, project_id: UUID, user_id: UUID) -> Project:
    project = db.scalar(select(Project).where(Project.id == project_id, Project.user_id == user_id))
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project was not found.")
    return project


def _get_owned_profile(db: Session, profile_id: UUID, user_id: UUID) -> AuthProfile:
    profile = db.scalar(
        select(AuthProfile)
        .join(Project, Project.id == AuthProfile.project_id)
        .where(AuthProfile.id == profile_id, Project.user_id == user_id)
    )
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Auth profile was not found.")
    return profile


def _validate_profile_against_project(
    project: Project,
    auth_type: str,
    login_url: str | None,
    storage_state_path: str | None,
) -> None:
    if auth_type == "form" and not login_url:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Form auth requires a login URL.")
    if auth_type == "storage_state" and not storage_state_path:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Storage-state auth requires a storage state path.",
        )
    if login_url and urlparse(login_url).netloc != urlparse(project.base_url).netloc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Login URL must use the same host as the project base URL.",
        )


def _read_profile(profile: AuthProfile) -> AuthProfileRead:
    return AuthProfileRead.model_validate(
        {
            **profile.__dict__,
            "password_configured": bool(profile.encrypted_password_value),
        }
    )
