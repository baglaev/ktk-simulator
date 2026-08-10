from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_session_broker, get_session_manager
from app.main import app


client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_live_manager():
    get_session_manager.cache_clear()
    get_session_broker.cache_clear()
    yield
    get_session_manager.cache_clear()
    get_session_broker.cache_clear()


def test_rest_contract_executes_complete_frontend_user_path() -> None:
    created = client.post(
        "/api/v1/sessions",
        json={
            "scenarioId": "MVP-SC-01",
            "traineeId": "trainee-api",
            "instructorId": "instructor-api",
            "mode": "training",
        },
    )
    session_id = created.json()["sessionId"]
    client.post(f"/api/v1/sessions/{session_id}/start")
    snapshot = client.post(
        f"/api/v1/sessions/{session_id}/advance",
        json={"dtMs": 55_000},
    ).json()

    def action(action_type: str, target_id: str, parameters: dict | None = None):
        nonlocal snapshot
        response = client.post(
            f"/api/v1/sessions/{session_id}/actions",
            json={
                "actionId": str(uuid4()),
                "sessionId": session_id,
                "actionType": action_type,
                "targetId": target_id,
                "parameters": parameters or {},
                "expectedStateVersion": snapshot["stateVersion"],
                "idempotencyKey": str(uuid4()),
                "submittedAt": datetime.now(timezone.utc).isoformat(),
            },
        )
        assert response.status_code == 200, response.text
        snapshot = response.json()

    action("open_equipment_card", "eq-n1a")
    action("view_signal", "PRA351")
    action("view_signal", "FYQR117")
    action(
        "submit_diagnosis",
        "eq-n1a",
        {"conclusion": "fault_detected", "reason": "bearing_wear"},
    )
    action("start_pump", "eq-n1b")
    action("stop_pump", "eq-n1a")
    action("view_signal", "PRA351")
    action("view_signal", "FYQR117")
    action("open_equipment_card", "eq-elou")
    action("open_equipment_card", "eq-e15")
    action("view_signal", "LRCA605")

    stable = client.post(
        f"/api/v1/sessions/{session_id}/advance",
        json={"dtMs": 30_000},
    )
    assert stable.status_code == 200
    assert client.get(f"/api/v1/sessions/{session_id}").json()["status"] == (
        "ready_to_complete"
    )

    completed = client.post(f"/api/v1/sessions/{session_id}/complete")
    result = client.get(f"/api/v1/sessions/{session_id}/result")
    actions = client.get(f"/api/v1/sessions/{session_id}/actions")

    assert completed.json()["status"] == "completed"
    assert result.status_code == 200
    assert result.json()["totalScore"] == 100
    assert result.json()["outcome"] == "success"
    assert actions.status_code == 200
    assert len(actions.json()) == 11
    assert actions.json()[0]["virtualTimeMs"] == 55_000


def test_diagnosis_payload_is_validated_by_api_contract() -> None:
    created = client.post(
        "/api/v1/sessions",
        json={
            "scenarioId": "MVP-SC-01",
            "traineeId": "trainee-validation",
            "mode": "training",
        },
    ).json()
    session_id = created["sessionId"]
    client.post(f"/api/v1/sessions/{session_id}/start")

    response = client.post(
        f"/api/v1/sessions/{session_id}/actions",
        json={
            "actionId": str(uuid4()),
            "sessionId": session_id,
            "actionType": "submit_diagnosis",
            "targetId": "eq-n1a",
            "parameters": {"conclusion": "made-up", "reason": "unknown"},
            "expectedStateVersion": 0,
            "idempotencyKey": str(uuid4()),
            "submittedAt": datetime.now(timezone.utc).isoformat(),
        },
    )

    assert response.status_code == 422


def test_unknown_action_target_is_rejected() -> None:
    created = client.post(
        "/api/v1/sessions",
        json={
            "scenarioId": "MVP-SC-01",
            "traineeId": "trainee-invalid-target",
            "mode": "training",
        },
    ).json()
    session_id = created["sessionId"]
    client.post(f"/api/v1/sessions/{session_id}/start")

    response = client.post(
        f"/api/v1/sessions/{session_id}/actions",
        json={
            "actionId": str(uuid4()),
            "sessionId": session_id,
            "actionType": "view_signal",
            "targetId": "UNKNOWN",
            "parameters": {},
            "expectedStateVersion": 0,
            "idempotencyKey": str(uuid4()),
            "submittedAt": datetime.now(timezone.utc).isoformat(),
        },
    )

    assert response.status_code == 409
    assert "unknown signal" in response.json()["detail"]
