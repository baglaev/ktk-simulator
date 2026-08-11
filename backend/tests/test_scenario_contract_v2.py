from uuid import UUID

import pytest
from pydantic import ValidationError

from app.domain import (
    CreateSessionRequest,
    ScenarioActionRequest,
    ScenarioHintMessage,
    TrainingMode,
)
from app.services import InvalidSessionTransitionError, SessionManager


def _session(manager: SessionManager, mode: TrainingMode = TrainingMode.TRAINING):
    created = manager.create_session(
        CreateSessionRequest(
            scenario_id="MVP-SC-01",
            trainee_id="contract-v2",
            mode=mode,
        )
    )
    manager.start_session(created.session_id)
    return created.session_id


def test_no_fault_diagnosis_omits_reason_and_fault_requires_reason() -> None:
    accepted = ScenarioActionRequest.model_validate(
        {
            "actionType": "submit_diagnosis",
            "targetId": "eq-n1a",
            "parameters": {"conclusion": "no_fault"},
        }
    )
    assert accepted.parameters == {"conclusion": "no_fault"}

    with pytest.raises(ValidationError, match="reason is required"):
        ScenarioActionRequest.model_validate(
            {
                "actionType": "submit_diagnosis",
                "targetId": "eq-n1a",
                "parameters": {"conclusion": "fault_detected"},
            }
        )

    with pytest.raises(ValidationError, match="must be omitted"):
        ScenarioActionRequest.model_validate(
            {
                "actionType": "submit_diagnosis",
                "targetId": "eq-n1a",
                "parameters": {"conclusion": "no_fault", "reason": "bearing_wear"},
            }
        )


def test_training_mode_emits_hint_and_control_mode_does_not() -> None:
    training_events: list[ScenarioHintMessage] = []
    training = SessionManager(
        event_publisher=lambda _session_id, event: training_events.append(event)
    )
    training_id = _session(training)
    training.advance_session(training_id, 10_000)

    control_events: list[ScenarioHintMessage] = []
    control = SessionManager(
        event_publisher=lambda _session_id, event: control_events.append(event)
    )
    control_id = _session(control, TrainingMode.CONTROL)
    control.advance_session(control_id, 10_000)

    assert [item.hint_id for item in training_events] == ["inspect-n1a"]
    assert training.list_hints(training_id)[0].virtual_time_ms == 10_000
    assert control_events == []
    assert control.list_hints(control_id) == []


def test_critical_limit_auto_completes_with_extended_result() -> None:
    manager = SessionManager()
    session_id = _session(manager)

    snapshot = manager.advance_session(session_id, 120_000)
    result = manager.get_result(session_id)

    assert snapshot.scenario_state.status.value == "completed"
    assert snapshot.scenario_state.completion_reason.value == "critical_limit_reached"
    assert result.status.value == "failed"
    assert result.completion_reason.value == "critical_limit_reached"
    assert result.elapsed_time_ms == 120_000
    assert len(result.task_execution) == 3
    assert {item.parameter_id for item in result.controlled_parameters} >= {
        "PRA351",
        "FYQR117",
        "LRCA605",
        "COMPAX.N1A.VELOCITY",
    }


def test_ai_analysis_is_persisted_and_does_not_change_result() -> None:
    manager = SessionManager()
    session_id = _session(manager)
    manager.advance_session(session_id, 120_000)
    result_before = manager.get_result(session_id)

    analysis = manager.generate_ai_analysis(session_id)
    stored = manager.get_ai_analysis(session_id)
    result_after = manager.get_result(session_id)

    assert stored == analysis
    assert analysis.total_score == result_before.total_score
    assert analysis.result_status == result_before.status
    assert analysis.provenance.score_changed is False
    assert result_after == result_before
    assert analysis.errors
    assert [item.detected_at_ms for item in analysis.errors] == sorted(
        item.detected_at_ms for item in analysis.errors
    )
    assert manager.get_adaptive_plan(session_id).items


def test_rag_is_forbidden_during_active_scenario_before_index_is_used() -> None:
    manager = SessionManager()
    session_id = _session(manager)

    with pytest.raises(InvalidSessionTransitionError, match="only after"):
        manager.ask_post_session_assistant(session_id, "Что происходит с Н-1А?")
