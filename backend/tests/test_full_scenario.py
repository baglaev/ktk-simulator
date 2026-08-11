from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.domain import (
    ACTION_ERROR_DESCRIPTIONS,
    ActionErrorCode,
    ActionType,
    CreateSessionRequest,
    OperatorAction,
    SessionStatus,
    TrainingMode,
)
from app.services import SessionManager


def test_every_action_error_has_a_human_readable_result_description() -> None:
    assert set(ACTION_ERROR_DESCRIPTIONS) == set(ActionErrorCode)
    assert all(
        description != code.value
        for code, description in ACTION_ERROR_DESCRIPTIONS.items()
    )


def _started_manager() -> tuple[SessionManager, UUID]:
    manager = SessionManager()
    session = manager.create_session(
        CreateSessionRequest(
            scenario_id="MVP-SC-01",
            trainee_id="trainee-001",
            instructor_id="instructor-001",
            mode=TrainingMode.TRAINING,
        )
    )
    manager.start_session(session.session_id)
    return manager, session.session_id


def _action(
    manager: SessionManager,
    session_id: UUID,
    action_type: ActionType,
    target_id: str,
    parameters: dict | None = None,
):
    snapshot = manager.get_snapshot(session_id)
    return manager.apply_action(
        session_id,
        OperatorAction(
            action_id=uuid4(),
            session_id=session_id,
            action_type=action_type,
            target_id=target_id,
            parameters=parameters or {},
            expected_state_version=snapshot.state_version,
            idempotency_key=str(uuid4()),
            submitted_at=datetime.now(timezone.utc),
        ),
    )


def _values(snapshot) -> dict[str, float]:
    return {
        item.parameter_id: item.value
        for component in snapshot.components
        for item in component.parameters
    }


def _perform_switch(
    manager: SessionManager,
    session_id: UUID,
    *,
    correct_diagnosis: bool = True,
) -> None:
    _action(manager, session_id, ActionType.OPEN_EQUIPMENT_CARD, "eq-n1a")
    _action(manager, session_id, ActionType.VIEW_SIGNAL, "PRA351")
    _action(manager, session_id, ActionType.VIEW_SIGNAL, "FYQR117")
    _action(manager, session_id, ActionType.RUN_DIAGNOSTICS, "eq-n1a")
    _action(
        manager,
        session_id,
        ActionType.SUBMIT_DIAGNOSIS,
        "eq-n1a",
        {"diagnosis": "1" if correct_diagnosis else "0"},
    )
    _action(manager, session_id, ActionType.START_PUMP, "eq-n1b")
    _action(manager, session_id, ActionType.STOP_PUMP, "eq-n1a")


def _perform_consequence_checks(manager: SessionManager, session_id: UUID) -> None:
    _action(manager, session_id, ActionType.VIEW_SIGNAL, "PRA351")
    _action(manager, session_id, ActionType.VIEW_SIGNAL, "FYQR117")
    _action(manager, session_id, ActionType.OPEN_EQUIPMENT_CARD, "eq-elou")
    _action(manager, session_id, ActionType.OPEN_EQUIPMENT_CARD, "eq-e15")
    _action(manager, session_id, ActionType.VIEW_SIGNAL, "LRCA605")


def test_correct_path_recovers_in_30_seconds_and_scores_100() -> None:
    manager, session_id = _started_manager()
    manager.advance_session(session_id, 55_000)
    _perform_switch(manager, session_id)

    switched = manager.get_snapshot(session_id)
    components = {item.component_id: item for item in switched.components}
    assert components["eq-n1a"].operating_state.value == "stopped"
    assert components["eq-n1a"].parameters == []
    assert components["eq-n1b"].operating_state.value == "running"
    assert len(components["eq-n1b"].parameters) == 5
    assert components["eq-n1-discharge"].state["recoveryActive"] is True

    _perform_consequence_checks(manager, session_id)
    halfway = manager.advance_session(session_id, 15_000)
    assert _values(halfway)["PRA351"] == 93.0
    assert _values(halfway)["FYQR117"] == 91.0
    assert _values(halfway)["ELOU.STAGE1.LEVEL"] == 99.0

    stable = manager.advance_session(session_id, 15_000)
    values = _values(stable)
    assert values["PRA351"] == 100
    assert values["FYQR117"] == 100
    assert values["ELOU.STAGE1.LEVEL"] == 100
    assert values["ELOU.STAGE2.LEVEL"] == 100
    assert values["LRCA605"] == 65
    completed = manager.get_session(session_id)
    result = manager.get_result(session_id)
    assert completed.status is SessionStatus.COMPLETED
    assert result.outcome.value == "success"
    assert result.total_score == 100
    assert result.error_codes == []
    assert len(manager.list_actions(session_id)) == 12


def test_wrong_diagnosis_does_not_block_physical_recovery() -> None:
    manager, session_id = _started_manager()
    manager.advance_session(session_id, 55_000)
    _perform_switch(manager, session_id, correct_diagnosis=False)
    _perform_consequence_checks(manager, session_id)
    manager.advance_session(session_id, 30_000)

    result = manager.get_result(session_id)

    assert result.outcome.value == "failed"
    assert result.total_score < 100
    assert "wrong_diagnosis_reason" in {
        item.value for item in result.error_codes
    }
    assert "switch_before_diagnosis" in {item.value for item in result.error_codes}


def test_wrong_diagnosis_then_correction_gets_half_diagnosis_credit() -> None:
    manager, session_id = _started_manager()
    manager.advance_session(session_id, 55_000)
    _action(manager, session_id, ActionType.OPEN_EQUIPMENT_CARD, "eq-n1a")
    _action(manager, session_id, ActionType.VIEW_SIGNAL, "PRA351")
    _action(manager, session_id, ActionType.VIEW_SIGNAL, "FYQR117")
    _action(manager, session_id, ActionType.RUN_DIAGNOSTICS, "eq-n1a")
    _action(
        manager,
        session_id,
        ActionType.SUBMIT_DIAGNOSIS,
        "eq-n1a",
        {"conclusion": "no_fault"},
    )
    _action(
        manager,
        session_id,
        ActionType.SUBMIT_DIAGNOSIS,
        "eq-n1a",
        {"conclusion": "fault_detected", "reason": "bearing_wear"},
    )
    _action(manager, session_id, ActionType.START_PUMP, "eq-n1b")
    _action(manager, session_id, ActionType.STOP_PUMP, "eq-n1a")
    _perform_consequence_checks(manager, session_id)
    manager.advance_session(session_id, 30_000)
    result = manager.get_result(session_id)
    error_codes = {item.value for item in result.error_codes}

    assert result.diagnosis.score == 17
    assert result.total_score == 92
    assert "wrong_diagnosis_corrected" in error_codes
    assert "fault_not_detected" in error_codes


def test_stopping_healthy_pump_is_persisted_and_penalized() -> None:
    manager, session_id = _started_manager()
    manager.advance_session(session_id, 20_000)
    _action(manager, session_id, ActionType.STOP_PUMP, "eq-n1")
    manager.complete_session(session_id)

    result = manager.get_result(session_id)
    error_codes = {item.value for item in result.error_codes}
    stored_action = manager.list_actions(session_id)[0]

    assert "healthy_pump_stopped" in error_codes
    assert "multiple_pumps_stopped" in error_codes
    assert result.penalties == -10
    assert stored_action.error_codes


def test_correct_faulty_pump_with_wrong_reason_keeps_identification_points() -> None:
    manager, session_id = _started_manager()
    manager.advance_session(session_id, 20_000)
    _action(manager, session_id, ActionType.OPEN_EQUIPMENT_CARD, "eq-n1a")
    _action(manager, session_id, ActionType.VIEW_SIGNAL, "PRA351")
    _action(manager, session_id, ActionType.VIEW_SIGNAL, "FYQR117")
    _action(
        manager,
        session_id,
        ActionType.SUBMIT_DIAGNOSIS,
        "eq-n1a",
        {"conclusion": "fault_detected", "reason": "cavitation"},
    )
    manager.complete_session(session_id)

    result = manager.get_result(session_id)

    assert result.diagnosis.score == 18
    assert "wrong_diagnosis_reason" in {
        item.value for item in result.error_codes
    }


def test_recovery_can_finish_after_120_seconds_if_started_above_limit() -> None:
    manager, session_id = _started_manager()
    manager.advance_session(session_id, 119_000)
    _perform_switch(manager, session_id)
    _perform_consequence_checks(manager, session_id)

    snapshot = manager.advance_session(session_id, 30_000)

    assert snapshot.timing.elapsed_ms == 149_000
    assert snapshot.timing.progress_percent == 100
    assert snapshot.timing.remaining_ms == 0
    assert _values(snapshot)["LRCA605"] == 65
    assert manager.get_session(session_id).status is SessionStatus.COMPLETED
    assert not any(
        "критической границы" in item.description
        for item in snapshot.journal
    )


def test_no_switch_reaches_lrca_limit_and_fails_automatically() -> None:
    manager, session_id = _started_manager()

    manager.advance_session(session_id, 120_000)

    assert manager.get_session(session_id).status is SessionStatus.FAILED
    result = manager.get_result(session_id)
    assert result.outcome.value == "failed"
    assert "e15_safety_limit_reached" in {
        item.value for item in result.error_codes
    }
    assert "warning_ignored" in {item.value for item in result.error_codes}
    assert result.critical_failure_reasons
