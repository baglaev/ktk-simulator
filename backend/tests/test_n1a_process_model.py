from datetime import datetime, timezone
from uuid import UUID

import pytest

from app.domain import ActionType, OperatorAction, SignalQuality
from app.scenarios import load_n1a_scenario
from app.simulation import (
    ModelNotInitializedError,
    N1AProcessModel,
    SimulationCompletedError,
    StateVersionConflictError,
    load_n1a_model_profile,
)


SESSION_ID = UUID("11111111-1111-1111-1111-111111111111")


def create_model() -> N1AProcessModel:
    return N1AProcessModel(
        scenario=load_n1a_scenario(),
        profile=load_n1a_model_profile(),
    )


def signal_map(snapshot):
    return {item.signal_id: item for item in snapshot.signals}


def test_model_requires_initialization() -> None:
    with pytest.raises(ModelNotInitializedError):
        create_model().get_snapshot()


def test_initial_snapshot_contains_complete_model_state() -> None:
    snapshot = create_model().initialize(SESSION_ID)
    signals = signal_map(snapshot)
    n1a = next(item for item in snapshot.equipment if item.equipment_id == "eq-n1a")

    assert snapshot.sequence_no == 0
    assert snapshot.state_version == 0
    assert snapshot.virtual_time_ms == 0
    assert snapshot.scenario_version == "0.1.0"
    assert snapshot.model_version == "0.1.0"
    assert len(snapshot.equipment) == 22
    assert len(snapshot.signals) == 32
    assert signals["PRA351"].value == 100
    assert signals["FYQR117"].value == 100
    assert signals["LRCA602"].value is None
    assert signals["LRCA602"].quality is SignalQuality.UNCERTAIN
    assert n1a.state == {"faultSeverity": 0.0, "diagnosticStatus": "normal"}
    assert [item.event_type for item in snapshot.events] == ["scenario_initialized"]


def test_model_interpolates_between_keyframes() -> None:
    model = create_model()
    model.initialize(SESSION_ID)

    snapshot = model.step(32_500)
    signals = signal_map(snapshot)

    assert signals["PRA351"].value == 97.5
    assert signals["FYQR117"].value == 96.5
    assert signals["COMPAX.N1A.VELOCITY"].value == 7.9
    assert signals["COMPAX.N1.VELOCITY"].value == 2.4


def test_model_emits_events_crossed_by_large_step() -> None:
    model = create_model()
    model.initialize(SESSION_ID)

    snapshot = model.step(55_000)

    assert [item.event_type for item in snapshot.events] == [
        "scenario_initialized",
        "diagnostic_warning",
        "diagnostic_critical",
        "feed_parameters_declining",
        "elou_level_declining",
    ]


def test_two_runs_with_same_inputs_are_identical() -> None:
    first = create_model()
    second = create_model()
    first.initialize(SESSION_ID)
    second.initialize(SESSION_ID)

    first_snapshot = first.step(80_000)
    second_snapshot = second.step(80_000)

    assert first_snapshot.model_dump(mode="json") == second_snapshot.model_dump(
        mode="json"
    )


def test_terminal_snapshot_uses_training_boundaries() -> None:
    model = create_model()
    model.initialize(SESSION_ID)

    snapshot = model.step(120_000)
    signals = signal_map(snapshot)

    assert snapshot.virtual_time_ms == 120_000
    assert signals["PRA351"].value == 38
    assert signals["FYQR117"].value == 34
    assert signals["LRCA605"].value == 20
    assert signals["LSA641A"].value is True
    assert signals["LS644A"].value is False
    assert snapshot.events[-1].event_type == "training_scenario_boundary_reached"

    with pytest.raises(SimulationCompletedError):
        model.step(1_000)


def test_action_is_recorded_without_changing_virtual_time() -> None:
    model = create_model()
    model.initialize(SESSION_ID)
    action = OperatorAction(
        action_id=UUID("22222222-2222-2222-2222-222222222222"),
        session_id=SESSION_ID,
        action_type=ActionType.VIEW_SIGNAL,
        target_id="PRA351",
        expected_state_version=0,
        idempotency_key="view-pra351-1",
        submitted_at=datetime(2026, 8, 7, 12, 0, tzinfo=timezone.utc),
    )

    snapshot = model.apply_action(action)

    assert snapshot.virtual_time_ms == 0
    assert snapshot.sequence_no == 1
    assert snapshot.state_version == 1
    assert snapshot.events[-1].event_type == "operator_action_recorded"
    assert snapshot.events[-1].payload["actionType"] == "view_signal"


def test_action_rejects_stale_state_version() -> None:
    model = create_model()
    model.initialize(SESSION_ID)
    model.step(1_000)
    action = OperatorAction(
        action_id=UUID("22222222-2222-2222-2222-222222222222"),
        session_id=SESSION_ID,
        action_type=ActionType.RUN_DIAGNOSTICS,
        target_id="eq-n1a",
        expected_state_version=0,
        idempotency_key="diagnostics-n1a-1",
        submitted_at=datetime(2026, 8, 7, 12, 0, tzinfo=timezone.utc),
    )

    with pytest.raises(StateVersionConflictError):
        model.apply_action(action)


def test_snapshot_serializes_model_metadata_in_camel_case() -> None:
    snapshot = create_model().initialize(SESSION_ID)
    payload = snapshot.model_dump(mode="json", by_alias=True)

    assert payload["sequenceNo"] == 0
    assert payload["stateVersion"] == 0
    assert payload["virtualTimeMs"] == 0
    assert payload["equipment"][0]["equipmentId"]
