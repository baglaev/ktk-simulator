from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, Field, JsonValue, model_validator

from app.domain.base import APIModel
from app.domain.enums import (
    ActionErrorCode,
    ActionType,
    DiagnosisConclusion,
    DiagnosisReason,
)


class ScenarioActionRequest(APIModel):
    """Minimal action payload received from frontend over WebSocket."""

    action_type: ActionType
    target_id: str | None = None
    parameters: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_action_payload(self) -> ScenarioActionRequest:
        _validate_action_payload(
            self.action_type,
            self.target_id,
            self.parameters,
        )
        return self


class ActionAcceptedMessage(APIModel):
    """Acknowledgement sent after an action has been applied and persisted."""

    type: Literal["action.result"] = "action.result"
    status: Literal["accepted"] = "accepted"
    action_id: UUID
    state_version: int = Field(ge=0)


class ActionErrorDetail(APIModel):
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)


class ActionRejectedMessage(APIModel):
    """Stable WebSocket error envelope for an invalid or rejected action."""

    type: Literal["action.result"] = "action.result"
    status: Literal["rejected"] = "rejected"
    error: ActionErrorDetail


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
        _validate_action_payload(
            self.action_type,
            self.target_id,
            self.parameters,
        )
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


def _validate_action_payload(
    action_type: ActionType,
    target_id: str | None,
    parameters: dict[str, JsonValue],
) -> None:
    if action_type in {
        ActionType.OPEN_EQUIPMENT_CARD,
        ActionType.VIEW_SIGNAL,
        ActionType.RUN_DIAGNOSTICS,
    } and not target_id:
        raise ValueError(f"targetId is required for {action_type.value}")
    if action_type is ActionType.SUBMIT_DIAGNOSIS:
        if not target_id:
            raise ValueError("targetId is required for submit_diagnosis")
        try:
            conclusion = DiagnosisConclusion(parameters.get("conclusion"))
        except (TypeError, ValueError) as error:
            raise ValueError(
                "submit_diagnosis requires a valid conclusion"
            ) from error
        reason = parameters.get("reason")
        if conclusion is DiagnosisConclusion.FAULT_DETECTED:
            try:
                parsed_reason = DiagnosisReason(reason)
            except (TypeError, ValueError) as error:
                raise ValueError(
                    "reason is required when conclusion is fault_detected"
                ) from error
            if parsed_reason is DiagnosisReason.UNKNOWN:
                raise ValueError("reason must be one of the diagnostic options")
        elif reason is not None:
            raise ValueError("reason must be omitted when conclusion is no_fault")
    if action_type in {ActionType.START_PUMP, ActionType.STOP_PUMP}:
        if not target_id:
            raise ValueError("targetId is required for a pump command")
