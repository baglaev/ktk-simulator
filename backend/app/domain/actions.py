from __future__ import annotations

from uuid import UUID

from pydantic import AwareDatetime, Field, JsonValue, model_validator

from app.domain.base import APIModel
from app.domain.enums import (
    ActionErrorCode,
    ActionType,
    DiagnosisConclusion,
    DiagnosisReason,
)


class OperatorAction(APIModel):
    """A training-interface action, not a command to real equipment."""

    action_id: UUID
    session_id: UUID
    action_type: ActionType
    target_id: str | None = None
    parameters: dict[str, JsonValue] = Field(default_factory=dict)
    expected_state_version: int = Field(ge=0)
    idempotency_key: str = Field(min_length=1, max_length=128)
    submitted_at: AwareDatetime

    @model_validator(mode="after")
    def validate_action_payload(self) -> OperatorAction:
        if self.action_type is ActionType.SUBMIT_DIAGNOSIS:
            if not self.target_id:
                raise ValueError("targetId is required for submit_diagnosis")
            try:
                DiagnosisConclusion(self.parameters.get("conclusion"))
                DiagnosisReason(self.parameters.get("reason"))
            except (TypeError, ValueError) as error:
                raise ValueError(
                    "submit_diagnosis requires valid conclusion and reason"
                ) from error
        if self.action_type in {ActionType.START_PUMP, ActionType.STOP_PUMP}:
            if not self.target_id:
                raise ValueError("targetId is required for a pump command")
        return self


class RecordedAction(APIModel):
    """Accepted user action retained for audit, scoring and later AI review."""

    action_id: UUID
    session_id: UUID
    sequence_no: int = Field(ge=1)
    virtual_time_ms: int = Field(ge=0)
    action_type: ActionType
    target_id: str | None = None
    parameters: dict[str, JsonValue] = Field(default_factory=dict)
    description: str = Field(min_length=1)
    error_codes: list[ActionErrorCode] = Field(default_factory=list)
    submitted_at: AwareDatetime
