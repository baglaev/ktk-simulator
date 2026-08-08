"""Public data contracts shared by API, simulation model and frontend."""

from app.domain.actions import OperatorAction
from app.domain.base import APIModel, Provenance
from app.domain.enums import (
    ActionType,
    EquipmentStatus,
    EquipmentType,
    EventSeverity,
    GeneralStatus,
    MeasurementType,
    ParameterOrigin,
    SessionStatus,
    TrainingMode,
    UserRole,
)
from app.domain.equipment import (
    ComponentState,
    EquipmentDefinition,
    EquipmentParameterDefinition,
)
from app.domain.sessions import (
    AdvanceSessionRequest,
    CreateSessionRequest,
    TrainingSession,
)
from app.domain.scenarios import (
    EducationalAssumption,
    EquipmentConnection,
    ScenarioConfig,
    ScenarioSummary,
    SourceReference,
)
from app.domain.signals import ComponentParameterValue, SignalDefinition
from app.domain.telemetry import (
    JournalEntry,
    ModelSnapshot,
    ScenarioTiming,
    TelemetryUpdate,
)

__all__ = [
    "APIModel",
    "AdvanceSessionRequest",
    "ActionType",
    "CreateSessionRequest",
    "ComponentParameterValue",
    "ComponentState",
    "EquipmentDefinition",
    "EquipmentConnection",
    "EquipmentParameterDefinition",
    "EquipmentStatus",
    "EquipmentType",
    "EventSeverity",
    "GeneralStatus",
    "EducationalAssumption",
    "MeasurementType",
    "JournalEntry",
    "ModelSnapshot",
    "OperatorAction",
    "ParameterOrigin",
    "Provenance",
    "ScenarioConfig",
    "ScenarioSummary",
    "SessionStatus",
    "SignalDefinition",
    "SourceReference",
    "ScenarioTiming",
    "TelemetryUpdate",
    "TrainingMode",
    "TrainingSession",
    "UserRole",
]
