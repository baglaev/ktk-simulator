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


def test_websocket_contract_executes_complete_frontend_user_path() -> None:
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
    advanced = client.post(
        f"/api/v1/sessions/{session_id}/advance",
        json={"dtMs": 55_000},
    )
    assert advanced.status_code == 200

    with client.websocket_connect(
        f"/ws/v1/sessions/{session_id}"
    ) as websocket:
        snapshot = websocket.receive_json()

        def action(
            action_type: str,
            target_id: str,
            parameters: dict | None = None,
        ) -> None:
            nonlocal snapshot
            payload = {"actionType": action_type, "targetId": target_id}
            if parameters is not None:
                payload["parameters"] = parameters
            websocket.send_json(payload)
            result = websocket.receive_json()
            assert result["type"] == "action.result"
            assert result["status"] == "accepted"
            snapshot = websocket.receive_json()
            assert snapshot["type"] == "telemetry.update"
            assert snapshot["stateVersion"] == result["stateVersion"]

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
        stable_update = websocket.receive_json()

    assert stable.status_code == 200
    assert stable_update["type"] == "telemetry.update"
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

    with client.websocket_connect(
        f"/ws/v1/sessions/{session_id}"
    ) as websocket:
        websocket.receive_json()
        websocket.send_json(
            {
                "actionType": "submit_diagnosis",
                "targetId": "eq-n1a",
                "parameters": {
                    "conclusion": "made-up",
                    "reason": "unknown",
                },
            }
        )
        response = websocket.receive_json()

    assert response["status"] == "rejected"
    assert response["error"]["code"] == "invalid_action"


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

    with client.websocket_connect(
        f"/ws/v1/sessions/{session_id}"
    ) as websocket:
        websocket.receive_json()
        websocket.send_json(
            {"actionType": "view_signal", "targetId": "UNKNOWN"}
        )
        response = websocket.receive_json()

    assert response["status"] == "rejected"
    assert response["error"]["code"] == "action_rejected"
    assert "unknown signal" in response["error"]["message"]
