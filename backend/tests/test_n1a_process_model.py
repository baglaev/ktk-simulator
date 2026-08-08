from datetime import datetime, timezone
from uuid import UUID

import pytest

from app.domain import ActionType, GeneralStatus, OperatorAction
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


def component_map(snapshot):
    return {item.component_id: item for item in snapshot.components}


def parameter_map(snapshot):
    return {
        parameter.parameter_id: parameter
        for component in snapshot.components
        for parameter in component.parameters
    }


def test_model_requires_initialization() -> None:
    with pytest.raises(ModelNotInitializedError):
        create_model().get_snapshot()


def test_initial_snapshot_contains_complete_model_state() -> None:
    snapshot = create_model().initialize(SESSION_ID)
    parameters = parameter_map(snapshot)
    n1a = component_map(snapshot)["eq-n1a"]

    assert snapshot.sequence_no == 0
    assert snapshot.state_version == 0
    assert snapshot.timing.elapsed_ms == 0
    assert snapshot.timing.total_ms == 120_000
    assert snapshot.scenario_version == "0.2.0"
    assert snapshot.model_version == "0.2.0"
    assert len(snapshot.components) == 8
    assert len(parameters) == 27
    assert parameters["PRA351"].value_percent == 100
    assert parameters["FYQR117"].value_percent == 100
    assert parameters["COMPAX.N1V.VELOCITY"].value_percent == 100
    assert parameters["LRCA605"].value_percent == 65
    assert component_map(snapshot)["eq-n1v"].operating_state.value == "running"
    assert component_map(snapshot)["eq-n1b"].operating_state.value == "stopped"
    assert n1a.status is GeneralStatus.SUCCESS
    assert n1a.state == {"faultSeverityPercent": 0.0}
    assert [item.description for item in snapshot.journal] == [
        "Сценарий запущен"
    ]


def test_model_interpolates_between_keyframes() -> None:
    model = create_model()
    model.initialize(SESSION_ID)

    snapshot = model.step(32_500)
    parameters = parameter_map(snapshot)

    assert parameters["PRA351"].value_percent == 97.5
    assert parameters["FYQR117"].value_percent == 96.5
    assert parameters["COMPAX.N1A.VELOCITY"].value_percent == 328.1
    assert parameters["COMPAX.N1.VELOCITY"].value_percent == 100
    assert component_map(snapshot)["eq-n1a"].status is GeneralStatus.ALERT


def test_model_emits_events_crossed_by_large_step() -> None:
    model = create_model()
    model.initialize(SESSION_ID)

    snapshot = model.step(55_000)

    assert [item.time for item in snapshot.journal] == [
        "00:00",
        "00:10",
        "00:25",
        "00:40",
        "00:55",
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
    parameters = parameter_map(snapshot)

    assert snapshot.timing.elapsed_ms == 120_000
    assert snapshot.timing.remaining_ms == 0
    assert snapshot.timing.progress_percent == 100
    assert parameters["PRA351"].value_percent == 38
    assert parameters["FYQR117"].value_percent == 34
    assert parameters["LRCA605"].value_percent == 20
    assert parameters["ELOU.STAGE1.LEVEL"].value_percent == 72
    assert parameters["ELOU.STAGE2.LEVEL"].value_percent == 81
    assert snapshot.journal[-1].description == "Общее время сценария завершено"

    with pytest.raises(SimulationCompletedError):
        model.step(1_000)


def test_action_is_recorded_without_changing_elapsed_time() -> None:
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

    assert snapshot.timing.elapsed_ms == 0
    assert snapshot.sequence_no == 1
    assert snapshot.state_version == 1
    assert snapshot.journal[-1].time == "00:00"
    assert snapshot.journal[-1].description == "Просмотрен параметр PRA 351"


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
    assert payload["timing"]["mode"] == "live"
    assert payload["timing"]["elapsedMs"] == 0
    assert payload["components"][0]["componentId"]
    assert "signals" not in payload
