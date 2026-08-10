from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, Field, model_validator

from app.domain.base import APIModel
from app.domain.enums import SessionStatus, TrainingMode


class TrainingSession(APIModel):
    """Lifecycle state of one isolated training run."""

    session_id: UUID
    scenario_id: str = Field(min_length=1)
    scenario_version: str = Field(min_length=1)
    model_id: str = Field(min_length=1)
    model_version: str = Field(min_length=1)
    trainee_id: str = Field(min_length=1)
    instructor_id: str | None = None
    mode: TrainingMode
    status: SessionStatus = SessionStatus.CREATED
    time_mode: Literal["live"] = "live"
    elapsed_time_ms: int = Field(default=0, ge=0)
    total_duration_ms: int = Field(gt=0)
    state_version: int = Field(default=0, ge=0)
    created_at: AwareDatetime
    started_at: AwareDatetime | None = None
    completed_at: AwareDatetime | None = None

    @model_validator(mode="after")
    def validate_timestamps(self) -> TrainingSession:
        if self.started_at and self.started_at < self.created_at:
            raise ValueError("startedAt cannot be earlier than createdAt")
        if self.completed_at and self.completed_at < self.created_at:
            raise ValueError("completedAt cannot be earlier than createdAt")
        if self.completed_at and self.started_at and self.completed_at < self.started_at:
            raise ValueError("completedAt cannot be earlier than startedAt")
        return self


class CreateSessionRequest(APIModel):
    scenario_id: str = Field(min_length=1)
    trainee_id: str = Field(min_length=1)
    instructor_id: str | None = None
    mode: TrainingMode


class AdvanceSessionRequest(APIModel):
    """Explicit elapsed-time step used only by tests and manual debugging."""

    dt_ms: int = Field(gt=0)
