from __future__ import annotations

from uuid import UUID

from pydantic import AwareDatetime, Field, JsonValue

from app.domain.base import APIModel
from app.domain.enums import ActionType


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
