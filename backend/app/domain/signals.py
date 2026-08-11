from __future__ import annotations

from pydantic import Field

from app.domain.base import APIModel, Provenance
from app.domain.enums import GeneralStatus, MeasurementType


SignalScalar = float | int | bool | str | None


class SignalDefinition(APIModel):
    """Static metadata for a measured or calculated signal."""

    signal_id: str = Field(min_length=1)
    tag: str = Field(min_length=1)
    equipment_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    measurement_type: MeasurementType
    unit: str | None = Field(default=None, min_length=1)
    unit_provenance: Provenance | None = None
    precision: int | None = Field(default=None, ge=0, le=8)
    provenance: Provenance


class ComponentParameterValue(APIModel):
    """Frontend-ready value in its configured engineering unit."""

    parameter_id: str = Field(min_length=1)
    tag: str = Field(min_length=1)
    name: str = Field(min_length=1)
    measurement_type: MeasurementType
    value: float
    unit: str = Field(min_length=1)
    status: GeneralStatus
