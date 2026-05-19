from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

AgentType = Literal["explorer", "form", "navigation", "chaos", "visual", "auth", "regression"]


@dataclass(frozen=True)
class Viewport:
    width: int
    height: int


@dataclass(frozen=True)
class AgentJob:
    project_id: str
    test_run_id: str
    base_url: str
    agent_type: AgentType = "explorer"
    max_depth: int = 3
    max_duration_minutes: int = 30
    viewport: Viewport = Viewport(width=1440, height=900)
    allowed_patterns: list[str] = field(default_factory=list)
    excluded_patterns: list[str] = field(default_factory=list)
    safe_mode: bool = True
