"""Public data contracts shared by API, simulation model and frontend."""

from app.domain.actions import OperatorAction, RecordedAction
from app.domain.base import APIModel, Provenance
from app.domain.enums import (
    ActionType,
    ActionErrorCode,
    DiagnosisConclusion,
    DiagnosisReason,
    EquipmentStatus,
    EquipmentType,
    EventSeverity,
    GeneralStatus,
    MeasurementType,
    ParameterOrigin,
    SessionStatus,
    ScenarioOutcome,
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
from app.domain.results import ScoreSection, SessionResult
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
    "ActionErrorCode",
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
    "DiagnosisConclusion",
    "DiagnosisReason",
    "EducationalAssumption",
    "MeasurementType",
    "JournalEntry",
    "ModelSnapshot",
    "OperatorAction",
    "RecordedAction",
    "ParameterOrigin",
    "Provenance",
    "ScenarioConfig",
    "ScenarioSummary",
    "ScenarioOutcome",
    "ScoreSection",
    "SessionResult",
    "SessionStatus",
    "SignalDefinition",
    "SourceReference",
    "ScenarioTiming",
    "TelemetryUpdate",
    "TrainingMode",
    "TrainingSession",
    "UserRole",
]
