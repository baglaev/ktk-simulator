from __future__ import annotations

from uuid import UUID

from pydantic import AwareDatetime, Field

from app.domain.base import APIModel
from app.domain.enums import ActionErrorCode, ScenarioOutcome


class ScoreSection(APIModel):
    score: int = Field(ge=0)
    max_score: int = Field(gt=0)


class SessionResult(APIModel):
    """Deterministic SCR-04 result. AI assessment can be added separately."""

    session_id: UUID
    rubric_version: str = "SCR04-A18-1.0"
    outcome: ScenarioOutcome
    total_score: int = Field(ge=0, le=100)
    max_score: int = 100
    diagnosis: ScoreSection
    stabilization: ScoreSection
    consequence_control: ScoreSection
    timeliness: ScoreSection
    penalties: int = Field(le=0)
    error_codes: list[ActionErrorCode] = Field(default_factory=list)
    critical_failure_reasons: list[str] = Field(default_factory=list)
    completed_at: AwareDatetime
