from datetime import datetime, timezone
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_session_broker, get_session_manager
from app.main import app


client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_session_manager():
    get_session_manager.cache_clear()
    get_session_broker.cache_clear()
    yield
    get_session_manager.cache_clear()
    get_session_broker.cache_clear()


def create_session(trainee_id: str = "trainee-001") -> dict:
    response = client.post(
        "/api/v1/sessions",
        json={
            "scenarioId": "MVP-SC-01",
            "traineeId": trainee_id,
            "mode": "training",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_full_session_lifecycle() -> None:
    created = create_session()
    session_id = created["sessionId"]

    assert created["status"] == "created"
    assert created["timeMode"] == "live"
    assert created["elapsedTimeMs"] == 0
    assert created["totalDurationMs"] == 120_000

    started = client.post(f"/api/v1/sessions/{session_id}/start")
    assert started.status_code == 200
    assert started.json()["status"] == "running"

    advanced = client.post(
        f"/api/v1/sessions/{session_id}/advance",
        json={"dtMs": 10_000},
    )
    assert advanced.status_code == 200
    assert advanced.json()["timing"]["elapsedMs"] == 10_000
    assert advanced.json()["stateVersion"] == 1

    paused = client.post(f"/api/v1/sessions/{session_id}/pause")
    assert paused.status_code == 200
    assert paused.json()["status"] == "paused"

    blocked_advance = client.post(
        f"/api/v1/sessions/{session_id}/advance",
        json={"dtMs": 1_000},
    )
    assert blocked_advance.status_code == 409

    resumed = client.post(f"/api/v1/sessions/{session_id}/resume")
    assert resumed.status_code == 200
    assert resumed.json()["status"] == "running"

    completed = client.post(f"/api/v1/sessions/{session_id}/complete")
    assert completed.status_code == 200
    assert completed.json()["status"] == "failed"
    assert completed.json()["completedAt"] is not None

    result = client.get(f"/api/v1/sessions/{session_id}/result")
    assert result.status_code == 200
    assert result.json()["outcome"] == "failed"
    assert "completed_before_stable" in result.json()["errorCodes"]


def test_snapshot_requires_started_session() -> None:
    session_id = create_session()["sessionId"]

    response = client.get(f"/api/v1/sessions/{session_id}/snapshot")

    assert response.status_code == 409
    assert "must be started" in response.json()["detail"]


def test_unknown_session_returns_404() -> None:
    unknown_id = "99999999-9999-9999-9999-999999999999"

    response = client.get(f"/api/v1/sessions/{unknown_id}")

    assert response.status_code == 404


def test_two_sessions_have_isolated_model_state() -> None:
    first_id = create_session("trainee-001")["sessionId"]
    second_id = create_session("trainee-002")["sessionId"]
    client.post(f"/api/v1/sessions/{first_id}/start")
    client.post(f"/api/v1/sessions/{second_id}/start")

    client.post(
        f"/api/v1/sessions/{first_id}/advance",
        json={"dtMs": 25_000},
    )
    first_snapshot = client.get(
        f"/api/v1/sessions/{first_id}/snapshot"
    ).json()
    second_snapshot = client.get(
        f"/api/v1/sessions/{second_id}/snapshot"
    ).json()

    assert first_snapshot["timing"]["elapsedMs"] == 25_000
    assert second_snapshot["timing"]["elapsedMs"] == 0
    assert first_snapshot["stateVersion"] == 1
    assert second_snapshot["stateVersion"] == 0


def test_action_is_idempotent() -> None:
    session_id = create_session()["sessionId"]
    client.post(f"/api/v1/sessions/{session_id}/start")
    action_id = "22222222-2222-2222-2222-222222222222"
    payload = {
        "actionId": action_id,
        "sessionId": session_id,
        "actionType": "view_signal",
        "targetId": "PRA351",
        "expectedStateVersion": 0,
        "idempotencyKey": "view-pra351-1",
        "submittedAt": datetime(2026, 8, 8, 9, 0, tzinfo=timezone.utc).isoformat(),
    }

    first = client.post(
        f"/api/v1/sessions/{session_id}/actions",
        json=payload,
    )
    second = client.post(
        f"/api/v1/sessions/{session_id}/actions",
        json=payload,
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["stateVersion"] == 1
    assert second.json()["stateVersion"] == 1
    assert len(first.json()["journal"]) == len(second.json()["journal"])


def test_reusing_idempotency_key_for_another_action_returns_conflict() -> None:
    session_id = create_session()["sessionId"]
    client.post(f"/api/v1/sessions/{session_id}/start")
    base_payload = {
        "sessionId": session_id,
        "actionType": "view_signal",
        "targetId": "PRA351",
        "expectedStateVersion": 0,
        "idempotencyKey": "view-pra351-1",
        "submittedAt": datetime(2026, 8, 8, 9, 0, tzinfo=timezone.utc).isoformat(),
    }
    first_payload = {
        **base_payload,
        "actionId": "22222222-2222-2222-2222-222222222222",
    }
    second_payload = {
        **base_payload,
        "actionId": "33333333-3333-3333-3333-333333333333",
    }

    first = client.post(
        f"/api/v1/sessions/{session_id}/actions",
        json=first_payload,
    )
    second = client.post(
        f"/api/v1/sessions/{session_id}/actions",
        json=second_payload,
    )

    assert first.status_code == 200
    assert second.status_code == 409
    assert "idempotency key" in second.json()["detail"]


def test_action_rejects_path_session_mismatch() -> None:
    first_id = create_session("trainee-001")["sessionId"]
    second_id = create_session("trainee-002")["sessionId"]
    client.post(f"/api/v1/sessions/{first_id}/start")
    payload = {
        "actionId": "22222222-2222-2222-2222-222222222222",
        "sessionId": second_id,
        "actionType": "run_diagnostics",
        "targetId": "eq-n1a",
        "expectedStateVersion": 0,
        "idempotencyKey": "diagnostics-n1a-1",
        "submittedAt": datetime(2026, 8, 8, 9, 0, tzinfo=timezone.utc).isoformat(),
    }

    response = client.post(
        f"/api/v1/sessions/{first_id}/actions",
        json=payload,
    )

    assert response.status_code == 409


def test_create_session_rejects_unknown_scenario() -> None:
    response = client.post(
        "/api/v1/sessions",
        json={
            "scenarioId": "UNKNOWN",
            "traineeId": "trainee-001",
            "mode": "control",
        },
    )

    assert response.status_code == 404


def test_session_contract_uses_uuid() -> None:
    session = create_session()

    assert UUID(session["sessionId"])
