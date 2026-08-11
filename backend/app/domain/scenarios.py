from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from app.domain.base import APIModel, Provenance
from app.domain.enums import DiagnosisConclusion, DiagnosisReason, ParameterOrigin
from app.domain.equipment import EquipmentDefinition
from app.domain.signals import SignalDefinition


class SourceReference(APIModel):
    source_ref_id: str = Field(min_length=1)
    origin: Literal[ParameterOrigin.SOURCE, ParameterOrigin.TEAM]
    file_name: str = Field(min_length=1)
    section: str | None = None
    pages: str | None = None
    note: str | None = None


class EducationalAssumption(APIModel):
    assumption_id: str = Field(pattern=r"^A-[0-9]{2,}$")
    description: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    validation_status: Literal["pending", "approved", "rejected"] = "pending"


class EquipmentConnection(APIModel):
    connection_id: str = Field(min_length=1)
    source_equipment_id: str = Field(min_length=1)
    target_equipment_id: str = Field(min_length=1)
    stream_code: str = Field(min_length=1)
    description: str | None = None
    provenance: Provenance


class ScenarioSummary(APIModel):
    scenario_id: str = Field(min_length=1)
    scenario_version: str = Field(min_length=1)
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)


class DiagnosisChoice(APIModel):
    value: str = Field(min_length=1)
    label: str = Field(min_length=1)


class DiagnosisFormConfig(APIModel):
    """Stable frontend form contract; it never exposes the correct answer."""

    target_id: str = Field(min_length=1)
    conclusions: list[DiagnosisChoice] = Field(min_length=2)
    fault_reasons: list[DiagnosisChoice] = Field(min_length=1)
    provenance: Provenance

    @model_validator(mode="after")
    def validate_values(self) -> DiagnosisFormConfig:
        conclusions = {item.value for item in self.conclusions}
        if conclusions != {item.value for item in DiagnosisConclusion}:
            raise ValueError("diagnosis conclusions differ from action contract")
        reasons = {item.value for item in self.fault_reasons}
        supported_reasons = {
            item.value for item in DiagnosisReason if item is not DiagnosisReason.UNKNOWN
        }
        if reasons != supported_reasons:
            raise ValueError("diagnosis reasons differ from action contract")
        return self


class ScenarioConfig(APIModel):
    schema_version: Literal["1.0"] = "1.0"
    scenario_id: str = Field(min_length=1)
    scenario_version: str = Field(min_length=1)
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    diagnosis_form: DiagnosisFormConfig
    sources: list[SourceReference] = Field(default_factory=list)
    assumptions: list[EducationalAssumption] = Field(default_factory=list)
    equipment: list[EquipmentDefinition] = Field(default_factory=list)
    connections: list[EquipmentConnection] = Field(default_factory=list)
    signals: list[SignalDefinition] = Field(default_factory=list)

    def to_summary(self) -> ScenarioSummary:
        return ScenarioSummary(
            scenario_id=self.scenario_id,
            scenario_version=self.scenario_version,
            name=self.name,
            description=self.description,
        )

    @model_validator(mode="after")
    def validate_references(self) -> ScenarioConfig:
        source_ids = self._unique(
            [item.source_ref_id for item in self.sources], "source reference"
        )
        assumption_ids = self._unique(
            [item.assumption_id for item in self.assumptions], "assumption"
        )
        equipment_ids = self._unique(
            [item.equipment_id for item in self.equipment], "equipment"
        )
        self._unique([item.connection_id for item in self.connections], "connection")
        self._unique([item.signal_id for item in self.signals], "signal")

        for item in self.equipment:
            if item.parent_id and item.parent_id not in equipment_ids:
                raise ValueError(
                    f"unknown parent equipment ID '{item.parent_id}' for "
                    f"'{item.equipment_id}'"
                )
            self._validate_provenance(item.provenance, source_ids, assumption_ids)
            for parameter in item.specifications:
                self._validate_provenance(
                    parameter.provenance, source_ids, assumption_ids
                )

        for connection in self.connections:
            if connection.source_equipment_id not in equipment_ids:
                raise ValueError(
                    f"unknown connection source '{connection.source_equipment_id}'"
                )
            if connection.target_equipment_id not in equipment_ids:
                raise ValueError(
                    f"unknown connection target '{connection.target_equipment_id}'"
                )
            self._validate_provenance(
                connection.provenance, source_ids, assumption_ids
            )

        for signal in self.signals:
            if signal.equipment_id not in equipment_ids:
                raise ValueError(
                    f"unknown signal equipment ID '{signal.equipment_id}' for "
                    f"'{signal.signal_id}'"
                )
            self._validate_provenance(signal.provenance, source_ids, assumption_ids)
            if signal.unit_provenance:
                self._validate_provenance(
                    signal.unit_provenance, source_ids, assumption_ids
                )

        return self

    @staticmethod
    def _unique(values: list[str], object_name: str) -> set[str]:
        unique_values = set(values)
        if len(values) != len(unique_values):
            raise ValueError(f"duplicate {object_name} ID")
        return unique_values

    @staticmethod
    def _validate_provenance(
        provenance: Provenance,
        source_ids: set[str],
        assumption_ids: set[str],
    ) -> None:
        if (
            provenance.origin in {ParameterOrigin.SOURCE, ParameterOrigin.TEAM}
            and provenance.source_ref_id
            and provenance.source_ref_id not in source_ids
        ):
            raise ValueError(
                f"unknown source reference '{provenance.source_ref_id}'"
            )
        if (
            provenance.origin is ParameterOrigin.EDUCATIONAL_ASSUMPTION
            and provenance.assumption_id not in assumption_ids
        ):
            raise ValueError(
                f"unknown educational assumption '{provenance.assumption_id}'"
            )
