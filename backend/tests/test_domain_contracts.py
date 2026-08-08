from datetime import datetime, timezone
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.domain import (
    ActionType,
    EquipmentDefinition,
    EquipmentParameterDefinition,
    EquipmentState,
    EquipmentStatus,
    EquipmentType,
    MeasurementType,
    ModelSnapshot,
    OperatorAction,
    ParameterOrigin,
    Provenance,
    SessionStatus,
    SignalDefinition,
    SignalQuality,
    SignalValue,
    TelemetryDelta,
    TrainingMode,
    TrainingSession,
)


SESSION_ID = UUID("11111111-1111-1111-1111-111111111111")


def test_snapshot_serializes_to_frontend_camel_case() -> None:
    snapshot = ModelSnapshot(
        session_id=SESSION_ID,
        scenario_id="MVP-SC-01",
        scenario_version="0.1.0",
        model_id="n1a-deterministic-training-model",
        model_version="0.1.0",
        sequence_no=15,
        state_version=8,
        virtual_time_ms=120_000,
        equipment=[
            EquipmentState(
                equipment_id="N-1A",
                status=EquipmentStatus.RUNNING,
                state={"faultSeverity": 0.2},
            )
        ],
        signals=[
            SignalValue(
                signal_id="PRA351",
                value=86.0,
                quality=SignalQuality.GOOD,
                virtual_time_ms=120_000,
            )
        ],
    )

    payload = snapshot.model_dump(mode="json", by_alias=True)

    assert payload["type"] == "telemetry.snapshot"
    assert payload["sessionId"] == str(SESSION_ID)
    assert payload["sequenceNo"] == 15
    assert payload["stateVersion"] == 8
    assert payload["virtualTimeMs"] == 120_000
    assert payload["equipment"][0]["equipmentId"] == "N-1A"
    assert payload["signals"][0]["signalId"] == "PRA351"


def test_contract_accepts_camel_case_input() -> None:
    signal = SignalValue.model_validate(
        {
            "signalId": "FYQR117",
            "value": 90.0,
            "quality": "good",
            "virtualTimeMs": 1_000,
        }
    )

    assert signal.signal_id == "FYQR117"
    assert signal.virtual_time_ms == 1_000


def test_contract_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        SignalValue.model_validate(
            {
                "signalId": "PRA351",
                "value": 86.0,
                "quality": "good",
                "virtualTimeMs": 0,
                "unexpected": True,
            }
        )


def test_source_provenance_requires_source_reference() -> None:
    with pytest.raises(ValidationError, match="sourceRefId"):
        Provenance(origin=ParameterOrigin.SOURCE)


def test_educational_assumption_requires_assumption_id() -> None:
    with pytest.raises(ValidationError, match="assumptionId"):
        Provenance(origin=ParameterOrigin.EDUCATIONAL_ASSUMPTION)


def test_equipment_and_signal_definitions_keep_provenance() -> None:
    provenance = Provenance(
        origin=ParameterOrigin.SOURCE,
        source_ref_id="SRC-TECH-001",
    )
    equipment = EquipmentDefinition(
        equipment_id="N-1A",
        tag="N-1A",
        name="Сырьевой насос Н-1А",
        equipment_type=EquipmentType.PUMP,
        specifications=[
            EquipmentParameterDefinition(
                parameter_id="rated-capacity",
                name="Паспортная производительность",
                value=450,
                unit="source_unit",
                provenance=provenance,
            )
        ],
        provenance=provenance,
    )
    signal = SignalDefinition(
        signal_id="PRA351",
        tag="PRA351",
        equipment_id="LINE-N1-ELOU",
        name="Параметр линии PRA351",
        measurement_type=MeasurementType.PRESSURE,
        unit="source_unit",
        provenance=provenance,
    )

    assert equipment.provenance.source_ref_id == "SRC-TECH-001"
    assert equipment.specifications[0].provenance.source_ref_id == "SRC-TECH-001"
    assert signal.provenance.origin is ParameterOrigin.SOURCE


def test_training_session_and_operator_action_contracts() -> None:
    now = datetime(2026, 8, 7, 12, 0, tzinfo=timezone.utc)
    session = TrainingSession(
        session_id=SESSION_ID,
        scenario_id="N1A-DEVELOPING-FAULT",
        scenario_version="0.1.0",
        trainee_id="trainee-001",
        mode=TrainingMode.TRAINING,
        status=SessionStatus.CREATED,
        created_at=now,
    )
    action = OperatorAction(
        action_id=UUID("22222222-2222-2222-2222-222222222222"),
        session_id=session.session_id,
        action_type=ActionType.VIEW_SIGNAL,
        target_id="PRA351",
        expected_state_version=0,
        idempotency_key="action-001",
        submitted_at=now,
    )

    assert action.session_id == session.session_id
    assert action.action_type is ActionType.VIEW_SIGNAL


def test_empty_telemetry_delta_is_rejected() -> None:
    with pytest.raises(ValidationError, match="at least one change"):
        TelemetryDelta(
            session_id=SESSION_ID,
            scenario_id="MVP-SC-01",
            scenario_version="0.1.0",
            model_id="n1a-deterministic-training-model",
            model_version="0.1.0",
            sequence_no=2,
            state_version=2,
            virtual_time_ms=1_000,
        )
