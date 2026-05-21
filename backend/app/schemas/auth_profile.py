from __future__ import annotations

from datetime import datetime
from typing import Literal
from urllib.parse import urlparse
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

AuthProfileType = Literal["form", "storage_state"]


class AuthProfileBase(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    auth_type: AuthProfileType = "form"
    login_url: str | None = None
    username_selector: str | None = Field(default=None, max_length=500)
    password_selector: str | None = Field(default=None, max_length=500)
    submit_selector: str | None = Field(default=None, max_length=500)
    username_value: str | None = Field(default=None, max_length=500)
    storage_state_path: str | None = Field(default=None, max_length=1000)
    is_active: bool = True

    @field_validator("login_url")
    @classmethod
    def validate_login_url(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        cleaned = value.strip().rstrip("/")
        parsed = urlparse(cleaned)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Login URL must be a valid http or https URL.")
        return cleaned

    @field_validator(
        "username_selector",
        "password_selector",
        "submit_selector",
        "username_value",
        "storage_state_path",
    )
    @classmethod
    def strip_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class AuthProfileCreate(AuthProfileBase):
    password_value: str | None = Field(default=None, max_length=1000)


class AuthProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    auth_type: AuthProfileType | None = None
    login_url: str | None = None
    username_selector: str | None = Field(default=None, max_length=500)
    password_selector: str | None = Field(default=None, max_length=500)
    submit_selector: str | None = Field(default=None, max_length=500)
    username_value: str | None = Field(default=None, max_length=500)
    password_value: str | None = Field(default=None, max_length=1000)
    storage_state_path: str | None = Field(default=None, max_length=1000)
    is_active: bool | None = None

    @field_validator("login_url")
    @classmethod
    def validate_login_url(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        cleaned = value.strip().rstrip("/")
        parsed = urlparse(cleaned)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Login URL must be a valid http or https URL.")
        return cleaned

    @field_validator(
        "username_selector",
        "password_selector",
        "submit_selector",
        "username_value",
        "password_value",
        "storage_state_path",
    )
    @classmethod
    def strip_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class AuthProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    name: str
    auth_type: str
    login_url: str | None
    username_selector: str | None
    password_selector: str | None
    submit_selector: str | None
    username_value: str | None
    storage_state_path: str | None
    is_active: bool
    password_configured: bool = False
    created_at: datetime


class AuthProfileListResponse(BaseModel):
    auth_profiles: list[AuthProfileRead]
