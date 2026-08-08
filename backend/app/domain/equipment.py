from __future__ import annotations

from pydantic import Field, JsonValue

from app.domain.base import APIModel, Provenance
from app.domain.enums import EquipmentStatus, EquipmentType, GeneralStatus
from app.domain.signals import ComponentParameterValue


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


class ComponentState(APIModel):
    """Complete frontend state of one stable mnemonic-scheme component."""

    component_id: str = Field(min_length=1)
    ui_id: str = Field(min_length=1)
    tag: str = Field(min_length=1)
    name: str = Field(min_length=1)
    component_type: EquipmentType
    status: GeneralStatus
    operating_state: EquipmentStatus
    parameters: list[ComponentParameterValue] = Field(min_length=1)
    state: dict[str, JsonValue] = Field(default_factory=dict)
