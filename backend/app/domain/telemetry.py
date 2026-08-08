from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from app.domain.base import APIModel
from app.domain.equipment import ComponentState


class JournalEntry(APIModel):
    entry_id: UUID
    time: str = Field(pattern=r"^[0-9]{2,}:[0-5][0-9]$")
    description: str = Field(min_length=1)


class ScenarioTiming(APIModel):
    mode: Literal["live"] = "live"
    elapsed_ms: int = Field(ge=0)
    total_ms: int = Field(gt=0)
    remaining_ms: int = Field(ge=0)
    progress_percent: float = Field(ge=0, le=100)


class TelemetryEnvelope(APIModel):
    session_id: UUID
    scenario_id: str = Field(min_length=1)
    scenario_version: str = Field(min_length=1)
    model_id: str = Field(min_length=1)
    model_version: str = Field(min_length=1)
    sequence_no: int = Field(ge=0)
    state_version: int = Field(ge=0)
    timing: ScenarioTiming


class ModelSnapshot(TelemetryEnvelope):
    """Complete session state sent on connect and reconnect."""

    type: Literal["telemetry.snapshot"] = "telemetry.snapshot"
    components: list[ComponentState] = Field(min_length=1)
    journal: list[JournalEntry] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_unique_ids(self) -> ModelSnapshot:
        component_ids = [item.component_id for item in self.components]
        if len(component_ids) != len(set(component_ids)):
            raise ValueError("component IDs must be unique in a snapshot")
        return self


class TelemetryUpdate(TelemetryEnvelope):
    """Complete component list sent after each live model tick or action."""

    type: Literal["telemetry.update"] = "telemetry.update"
    components: list[ComponentState] = Field(min_length=1)
    journal: list[JournalEntry] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_components(self) -> TelemetryUpdate:
        if not self.components:
            raise ValueError("telemetry update must contain the component list")
        return self
