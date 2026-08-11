from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, Field

from app.domain.base import APIModel
from app.domain.enums import TrainingMode
from app.domain.results import TraineeResultSummary


class InstructorJournalItem(APIModel):
    time: str = Field(pattern=r"^[0-9]{2,}:[0-5][0-9]$")
    virtual_time_ms: int = Field(ge=0)
    kind: Literal["action", "hint"]
    description: str = Field(min_length=1)


class InstructorAttemptJournal(APIModel):
    session_id: UUID
    trainee_id: str = Field(min_length=1)
    mode: TrainingMode
    items: list[InstructorJournalItem] = Field(default_factory=list)


class InstructorResultItem(TraineeResultSummary):
    """Completed attempt enriched for the common instructor results table."""

    trainee_name: str = Field(min_length=1)
    journal: list[InstructorJournalItem] = Field(default_factory=list)


class InstructorResultsCollection(APIModel):
    items: list[InstructorResultItem] = Field(default_factory=list)
    total: int = Field(ge=0)


class InstructorTrainee(APIModel):
    """Sanitized trainee directory entry enriched with result statistics."""

    trainee_id: str = Field(min_length=1)
    login: str = Field(min_length=1)
    full_name: str = Field(min_length=1)
    assigned_instructor_id: str = Field(min_length=1)
    account_source: Literal["demo_directory", "session_history"]
    attempts_count: int = Field(ge=0)
    successful_attempts_count: int = Field(ge=0)
    average_score: int | None = Field(default=None, ge=0, le=100)
    best_score: int | None = Field(default=None, ge=0, le=100)
    last_completed_at: AwareDatetime | None = None
    latest_result: TraineeResultSummary | None = None


class InstructorTraineeList(APIModel):
    items: list[InstructorTrainee] = Field(default_factory=list)
    total: int = Field(ge=0)


class InstructorOverview(APIModel):
    total_trainees: int = Field(ge=0)
    trainees_with_attempts: int = Field(ge=0)
    completed_attempts: int = Field(ge=0)
    successful_attempts: int = Field(ge=0)
    average_score: int | None = Field(default=None, ge=0, le=100)
