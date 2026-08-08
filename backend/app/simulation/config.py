from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from app.domain import (
    APIModel,
    EquipmentStatus,
    EventSeverity,
    GeneralStatus,
    Provenance,
)
from app.domain.signals import SignalScalar


class NumericKeyframe(APIModel):
    time_ms: int = Field(ge=0)
    value: float


class DiscreteKeyframe(APIModel):
    time_ms: int = Field(ge=0)
    value: SignalScalar


class EquipmentStatusKeyframe(APIModel):
    time_ms: int = Field(ge=0)
    status: EquipmentStatus


class GeneralStatusKeyframe(APIModel):
    time_ms: int = Field(ge=0)
    status: GeneralStatus


class FaultStatusKeyframe(APIModel):
    time_ms: int = Field(ge=0)
    status: Literal["normal", "warning", "critical"]


class NumericTrajectory(APIModel):
    signal_id: str = Field(min_length=1)
    keyframes: list[NumericKeyframe] = Field(min_length=1)
    provenance: Provenance

    @model_validator(mode="after")
    def validate_times(self) -> NumericTrajectory:
        _validate_increasing_times(self.keyframes)
        return self


class DiscreteTrajectory(APIModel):
    signal_id: str = Field(min_length=1)
    keyframes: list[DiscreteKeyframe] = Field(min_length=1)
    provenance: Provenance

    @model_validator(mode="after")
    def validate_times(self) -> DiscreteTrajectory:
        _validate_increasing_times(self.keyframes)
        return self


class StaticSignalConfig(APIModel):
    signal_id: str = Field(min_length=1)
    value: SignalScalar = None
    status: GeneralStatus
    provenance: Provenance


class EquipmentStatusTimeline(APIModel):
    equipment_id: str = Field(min_length=1)
    keyframes: list[EquipmentStatusKeyframe] = Field(min_length=1)
    provenance: Provenance

    @model_validator(mode="after")
    def validate_times(self) -> EquipmentStatusTimeline:
        _validate_increasing_times(self.keyframes)
        return self


class ComponentStatusTimeline(APIModel):
    component_id: str = Field(min_length=1)
    keyframes: list[GeneralStatusKeyframe] = Field(min_length=1)
    provenance: Provenance

    @model_validator(mode="after")
    def validate_times(self) -> ComponentStatusTimeline:
        _validate_increasing_times(self.keyframes)
        return self


class FaultDevelopmentConfig(APIModel):
    equipment_id: str = Field(min_length=1)
    severity_keyframes: list[NumericKeyframe] = Field(min_length=1)
    status_keyframes: list[FaultStatusKeyframe] = Field(min_length=1)
    provenance: Provenance

    @model_validator(mode="after")
    def validate_times(self) -> FaultDevelopmentConfig:
        _validate_increasing_times(self.severity_keyframes)
        _validate_increasing_times(self.status_keyframes)
        if any(not 0 <= item.value <= 1 for item in self.severity_keyframes):
            raise ValueError("fault severity must be between 0 and 1")
        return self


class ScheduledModelEvent(APIModel):
    event_key: str = Field(min_length=1)
    time_ms: int = Field(ge=0)
    event_type: str = Field(min_length=1)
    severity: EventSeverity
    source_id: str | None = None
    description: str = Field(min_length=1)
    payload: dict[str, SignalScalar] = Field(default_factory=dict)
    provenance: Provenance


class ModelProfile(APIModel):
    schema_version: Literal["1.0"] = "1.0"
    model_id: str = Field(min_length=1)
    model_version: str = Field(min_length=1)
    scenario_id: str = Field(min_length=1)
    component_ids: list[str] = Field(min_length=1)
    tick_ms: int = Field(gt=0)
    total_duration_ms: int = Field(gt=0)
    fault: FaultDevelopmentConfig
    numeric_trajectories: list[NumericTrajectory] = Field(default_factory=list)
    discrete_trajectories: list[DiscreteTrajectory] = Field(default_factory=list)
    static_signals: list[StaticSignalConfig] = Field(default_factory=list)
    equipment_statuses: list[EquipmentStatusTimeline] = Field(default_factory=list)
    component_statuses: list[ComponentStatusTimeline] = Field(default_factory=list)
    scheduled_events: list[ScheduledModelEvent] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_profile(self) -> ModelProfile:
        signal_ids = [item.signal_id for item in self.numeric_trajectories]
        signal_ids.extend(item.signal_id for item in self.discrete_trajectories)
        signal_ids.extend(item.signal_id for item in self.static_signals)
        if len(signal_ids) != len(set(signal_ids)):
            raise ValueError("each signal must have exactly one model definition")

        equipment_ids = [item.equipment_id for item in self.equipment_statuses]
        if len(equipment_ids) != len(set(equipment_ids)):
            raise ValueError("duplicate equipment status timeline")

        if len(self.component_ids) != len(set(self.component_ids)):
            raise ValueError("duplicate frontend component ID")

        component_status_ids = [
            item.component_id for item in self.component_statuses
        ]
        if len(component_status_ids) != len(set(component_status_ids)):
            raise ValueError("duplicate component status timeline")
        if set(component_status_ids) != set(self.component_ids):
            raise ValueError(
                "component statuses must cover the frontend component list"
            )

        event_keys = [item.event_key for item in self.scheduled_events]
        if len(event_keys) != len(set(event_keys)):
            raise ValueError("duplicate scheduled event key")

        if any(
            item.time_ms > self.total_duration_ms
            for item in self.scheduled_events
        ):
            raise ValueError("scheduled event exceeds totalDurationMs")

        timelines = [self.fault.severity_keyframes, self.fault.status_keyframes]
        timelines.extend(item.keyframes for item in self.numeric_trajectories)
        timelines.extend(item.keyframes for item in self.discrete_trajectories)
        timelines.extend(item.keyframes for item in self.equipment_statuses)
        timelines.extend(item.keyframes for item in self.component_statuses)
        if any(
            item.time_ms > self.total_duration_ms
            for timeline in timelines
            for item in timeline
        ):
            raise ValueError("keyframe exceeds totalDurationMs")
        return self


def _validate_increasing_times(keyframes: list[object]) -> None:
    times = [getattr(item, "time_ms") for item in keyframes]
    if times != sorted(times) or len(times) != len(set(times)):
        raise ValueError("keyframe times must be strictly increasing")
