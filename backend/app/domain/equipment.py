from __future__ import annotations

from pydantic import Field, JsonValue

from app.domain.base import APIModel, Provenance
from app.domain.enums import EquipmentStatus, EquipmentType


class EquipmentParameterDefinition(APIModel):
    """One passport or configuration value with its own provenance."""

    parameter_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    value: JsonValue
    unit: str | None = None
    provenance: Provenance


class EquipmentDefinition(APIModel):
    """Static, versioned description of a process object."""

    equipment_id: str = Field(min_length=1)
    tag: str = Field(min_length=1)
    name: str = Field(min_length=1)
    equipment_type: EquipmentType
    parent_id: str | None = None
    specifications: list[EquipmentParameterDefinition] = Field(default_factory=list)
    provenance: Provenance


class EquipmentState(APIModel):
    """Calculated state of equipment at a point in virtual time."""

    equipment_id: str = Field(min_length=1)
    status: EquipmentStatus
    state: dict[str, JsonValue] = Field(default_factory=dict)
