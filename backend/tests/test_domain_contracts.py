from datetime import datetime, timezone
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.domain import (
    ActionType,
    ComponentParameterValue,
    ComponentState,
    EquipmentDefinition,
    EquipmentParameterDefinition,
    EquipmentStatus,
    EquipmentType,
    GeneralStatus,
    MeasurementType,
    ModelSnapshot,
    OperatorAction,
    ParameterOrigin,
    Provenance,
    ScenarioActionRequest,
    ScenarioRuntimeState,
    ScenarioRuntimeStatus,
    ScenarioTiming,
    SessionStatus,
    SignalDefinition,
    TelemetryUpdate,
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
        mode=TrainingMode.TRAINING,
        scenario_state=ScenarioRuntimeState(
            status=ScenarioRuntimeStatus.ACTIVE,
        ),
        timing=ScenarioTiming(
            elapsed_ms=120_000,
            total_ms=120_000,
            remaining_ms=0,
            progress_percent=100,
        ),
        components=[
            ComponentState(
                component_id="eq-n1a",
                ui_id="pump-h1a",
                tag="Н-1А",
                name="Сырьевой насос Н-1А",
                component_type=EquipmentType.PUMP,
                status=GeneralStatus.ALERT,
                operating_state=EquipmentStatus.RUNNING,
                parameters=[
                    ComponentParameterValue(
                        parameter_id="COMPAX.N1A.VELOCITY",
                        tag="COMPAX.N1A.VELOCITY",
                        name="Виброскорость Н-1А",
                        measurement_type=MeasurementType.VIBRATION_VELOCITY,
                        value=11.8,
                        unit="мм/с",
                        status=GeneralStatus.ALERT,
                    )
                ],
            )
        ],
    )

    payload = snapshot.model_dump(mode="json", by_alias=True)

    assert payload["type"] == "telemetry.snapshot"
    assert payload["sessionId"] == str(SESSION_ID)
    assert payload["sequenceNo"] == 15
    assert payload["stateVersion"] == 8
    assert payload["timing"]["mode"] == "live"
    assert payload["timing"]["elapsedMs"] == 120_000
    assert payload["components"][0]["componentId"] == "eq-n1a"
    assert payload["components"][0]["parameters"][0]["value"] == 11.8
    assert payload["components"][0]["parameters"][0]["unit"] == "мм/с"


def test_contract_accepts_camel_case_input() -> None:
    parameter = ComponentParameterValue.model_validate(
        {
            "parameterId": "FYQR117",
            "tag": "FYQR 117",
            "name": "Расход",
            "measurementType": "flow_rate",
            "value": 90.0,
            "unit": "%",
            "status": "warning",
        }
    )

    assert parameter.parameter_id == "FYQR117"
    assert parameter.status is GeneralStatus.WARNING


def test_contract_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        ComponentParameterValue.model_validate(
            {
                "parameterId": "PRA351",
                "tag": "PRA 351",
                "name": "Давление",
                "measurementType": "pressure",
                "value": 86.0,
                "unit": "%",
                "status": "success",
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
        model_id="n1a-model",
        model_version="0.1.0",
        trainee_id="trainee-001",
        mode=TrainingMode.TRAINING,
        status=SessionStatus.CREATED,
        total_duration_ms=120_000,
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


def test_websocket_action_request_has_minimal_strict_contract() -> None:
    action = ScenarioActionRequest.model_validate(
        {"actionType": "view_signal", "targetId": "PRA351"}
    )

    assert action.action_type is ActionType.VIEW_SIGNAL
    assert action.target_id == "PRA351"
    assert action.parameters == {}

    with pytest.raises(ValidationError, match="actionId"):
        ScenarioActionRequest.model_validate(
            {
                "actionType": "view_signal",
                "targetId": "PRA351",
                "actionId": "22222222-2222-2222-2222-222222222222",
            }
        )


def test_telemetry_update_without_components_is_rejected() -> None:
    with pytest.raises(ValidationError, match="components"):
        TelemetryUpdate(
            session_id=SESSION_ID,
            scenario_id="MVP-SC-01",
            scenario_version="0.1.0",
            model_id="n1a-deterministic-training-model",
            model_version="0.1.0",
            sequence_no=2,
            state_version=2,
            mode=TrainingMode.TRAINING,
            scenario_state=ScenarioRuntimeState(
                status=ScenarioRuntimeStatus.ACTIVE,
            ),
            timing=ScenarioTiming(
                elapsed_ms=1_000,
                total_ms=120_000,
                remaining_ms=119_000,
                progress_percent=0.8,
            ),
        )
