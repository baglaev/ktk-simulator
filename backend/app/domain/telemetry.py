from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import Field, JsonValue, model_validator

from app.domain.base import APIModel
from app.domain.enums import EventSeverity
from app.domain.equipment import EquipmentState
from app.domain.signals import SignalValue


class ModelEvent(APIModel):
    event_id: UUID
    event_type: str = Field(min_length=1)
    severity: EventSeverity
    source_id: str | None = None
    virtual_time_ms: int = Field(ge=0)
    payload: dict[str, JsonValue] = Field(default_factory=dict)


class TelemetryEnvelope(APIModel):
    session_id: UUID
    sequence_no: int = Field(ge=0)
    state_version: int = Field(ge=0)
    virtual_time_ms: int = Field(ge=0)


class ModelSnapshot(TelemetryEnvelope):
    """Complete session state sent on connect and reconnect."""

    type: Literal["telemetry.snapshot"] = "telemetry.snapshot"
    equipment: list[EquipmentState] = Field(default_factory=list)
    signals: list[SignalValue] = Field(default_factory=list)
    events: list[ModelEvent] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_unique_ids(self) -> ModelSnapshot:
        equipment_ids = [item.equipment_id for item in self.equipment]
        signal_ids = [item.signal_id for item in self.signals]
        if len(equipment_ids) != len(set(equipment_ids)):
            raise ValueError("equipment IDs must be unique in a snapshot")
        if len(signal_ids) != len(set(signal_ids)):
            raise ValueError("signal IDs must be unique in a snapshot")
        return self


class TelemetryDelta(TelemetryEnvelope):
    """Only values changed since the previous state version."""

    type: Literal["telemetry.delta"] = "telemetry.delta"
    equipment: list[EquipmentState] = Field(default_factory=list)
    signals: list[SignalValue] = Field(default_factory=list)
    events: list[ModelEvent] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_non_empty_delta(self) -> TelemetryDelta:
        if not (self.equipment or self.signals or self.events):
            raise ValueError("telemetry delta must contain at least one change")
        return self
