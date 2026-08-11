from __future__ import annotations

from uuid import UUID

from pydantic import AwareDatetime, Field, model_validator

from app.domain.base import APIModel
from app.domain.enums import (
    ActionErrorCode,
    CompletionReason,
    GeneralStatus,
    ResultStatus,
    ScenarioOutcome,
    SessionStatus,
    TrainingMode,
)


class ScoreSection(APIModel):
    score: int = Field(ge=0)
    max_score: int = Field(gt=0)


class TaskExecutionItem(APIModel):
    task_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    status: GeneralStatus
    completed_at_ms: int | None = Field(default=None, ge=0)
    description: str = Field(min_length=1)


class ResultParameter(APIModel):
    parameter_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    final_value: int
    minimum_value: int
    unit: str = Field(min_length=1)
    status: GeneralStatus


class ResultRemark(APIModel):
    code: str = Field(min_length=1)
    status: GeneralStatus
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)


class SessionResult(APIModel):
    """Deterministic SCR-04 result. AI assessment can be added separately."""

    session_id: UUID
    rubric_version: str = "SCR04-A18-2.0"
    status: ResultStatus
    outcome: ScenarioOutcome
    mode: TrainingMode
    completion_reason: CompletionReason
    summary: str = Field(min_length=1)
    elapsed_time_ms: int = Field(ge=0)
    total_score: int = Field(ge=0, le=100)
    max_score: int = 100
    diagnosis: ScoreSection
    stabilization: ScoreSection
    consequence_control: ScoreSection
    timeliness: ScoreSection
    penalties: int = Field(le=0)
    error_codes: list[ActionErrorCode] = Field(default_factory=list)
    critical_failure_reasons: list[str] = Field(default_factory=list)
    task_execution: list[TaskExecutionItem] = Field(default_factory=list)
    controlled_parameters: list[ResultParameter] = Field(default_factory=list)
    remarks: list[ResultRemark] = Field(default_factory=list)
    completed_at: AwareDatetime

    @model_validator(mode="before")
    @classmethod
    def adopt_legacy_scr04_payload(cls, value):
        """Read 0.3.x result JSON retained in an upgraded local database."""

        if not isinstance(value, dict) or (
            "status" in value or "resultStatus" in value
        ):
            return value
        payload = dict(value)
        outcome = payload.get("outcome", "failed")
        payload.update(
            {
                "status": "passed" if outcome == "success" else "failed",
                "mode": "training",
                "completionReason": (
                    "objectives_completed"
                    if outcome == "success"
                    else "completed_before_stabilization"
                ),
                "summary": "Архивный результат сессии версии 0.3.x.",
                "elapsedTimeMs": 0,
            }
        )
        return payload


class TraineeResultSummary(APIModel):
    """Compact completed-attempt row for the instructor dashboard."""

    session_id: UUID
    trainee_id: str = Field(min_length=1)
    instructor_id: str | None = None
    scenario_id: str = Field(min_length=1)
    scenario_version: str = Field(min_length=1)
    mode: TrainingMode
    session_status: SessionStatus
    result_status: ResultStatus
    outcome: ScenarioOutcome
    total_score: int = Field(ge=0, le=100)
    max_score: int = Field(gt=0)
    elapsed_time_ms: int = Field(ge=0)
    completed_at: AwareDatetime


class TraineeResultsPage(APIModel):
    """Paginated completed results returned to the instructor frontend."""

    items: list[TraineeResultSummary] = Field(default_factory=list)
    total: int = Field(ge=0)
    limit: int = Field(gt=0)
    offset: int = Field(ge=0)


class TraineeResultsCollection(APIModel):
    """All completed results returned without frontend query parameters."""

    items: list[TraineeResultSummary] = Field(default_factory=list)
    total: int = Field(ge=0)
