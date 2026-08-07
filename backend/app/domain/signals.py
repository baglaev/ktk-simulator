from __future__ import annotations

from pydantic import Field

from app.domain.base import APIModel, Provenance
from app.domain.enums import MeasurementType, SignalQuality


SignalScalar = float | int | bool | str | None


class SignalDefinition(APIModel):
    """Static metadata for a measured or calculated signal."""

    signal_id: str = Field(min_length=1)
    tag: str = Field(min_length=1)
    equipment_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    measurement_type: MeasurementType
    unit: str = Field(min_length=1)
    precision: int | None = Field(default=None, ge=0, le=8)
    provenance: Provenance


class SignalValue(APIModel):
    """Value produced by the model for a specific virtual time."""

    signal_id: str = Field(min_length=1)
    value: SignalScalar
    quality: SignalQuality = SignalQuality.GOOD
    virtual_time_ms: int = Field(ge=0)
