from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.api.dependencies import get_session_broker, get_session_manager
from app.main import app


client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_realtime_state():
    get_session_manager.cache_clear()
    get_session_broker.cache_clear()
    yield
    get_session_manager.cache_clear()
    get_session_broker.cache_clear()


def create_session(*, start: bool = True) -> str:
    response = client.post(
        "/api/v1/sessions",
        json={
            "scenarioId": "MVP-SC-01",
            "traineeId": "trainee-001",
            "mode": "training",
        },
    )
    assert response.status_code == 201
    session_id = response.json()["sessionId"]
    if start:
        started = client.post(f"/api/v1/sessions/{session_id}/start")
        assert started.status_code == 200
    return session_id


def test_websocket_sends_snapshot_then_full_update() -> None:
    session_id = create_session()

    with client.websocket_connect(
        f"/ws/v1/sessions/{session_id}"
    ) as websocket:
        snapshot = websocket.receive_json()
        advanced = client.post(
            f"/api/v1/sessions/{session_id}/advance",
            json={"dtMs": 10_000},
        )
        update = websocket.receive_json()

    assert advanced.status_code == 200
    assert snapshot["type"] == "telemetry.snapshot"
    assert snapshot["sequenceNo"] == 0
    assert update["type"] == "telemetry.update"
    assert update["sequenceNo"] == 1
    assert update["stateVersion"] == 1
    assert update["timing"]["elapsedMs"] == 10_000
    assert len(update["components"]) == 8
    assert [item["componentId"] for item in update["components"]] == [
        item["componentId"] for item in snapshot["components"]
    ]
    assert all("parameters" in item for item in update["components"])


def test_two_websocket_clients_receive_the_same_delta() -> None:
    session_id = create_session()

    with client.websocket_connect(
        f"/ws/v1/sessions/{session_id}"
    ) as first, client.websocket_connect(
        f"/ws/v1/sessions/{session_id}"
    ) as second:
        first.receive_json()
        second.receive_json()
        advanced = client.post(
            f"/api/v1/sessions/{session_id}/advance",
            json={"dtMs": 5_000},
        )
        first_delta = first.receive_json()
        second_delta = second.receive_json()

    assert advanced.status_code == 200
    assert first_delta == second_delta


def test_operator_action_is_streamed_in_journal() -> None:
    session_id = create_session()
    action = {
        "actionId": "22222222-2222-2222-2222-222222222222",
        "sessionId": session_id,
        "actionType": "run_diagnostics",
        "targetId": "eq-n1a",
        "expectedStateVersion": 0,
        "idempotencyKey": "diagnostics-n1a-1",
        "submittedAt": "2026-08-08T09:00:00+03:00",
    }

    with client.websocket_connect(
        f"/ws/v1/sessions/{session_id}"
    ) as websocket:
        websocket.receive_json()
        response = client.post(
            f"/api/v1/sessions/{session_id}/actions",
            json=action,
        )
        update = websocket.receive_json()

    assert response.status_code == 200
    assert update["type"] == "telemetry.update"
    assert update["sequenceNo"] == 1
    assert update["stateVersion"] == 1
    assert update["journal"][-1] == {
        "entryId": "22222222-2222-2222-2222-222222222222",
        "time": "00:00",
        "description": "Запущена диагностика компонента Н-1А",
    }


def test_unknown_session_is_closed_with_4404() -> None:
    unknown_id = "99999999-9999-9999-9999-999999999999"

    with pytest.raises(WebSocketDisconnect) as error:
        with client.websocket_connect(f"/ws/v1/sessions/{unknown_id}"):
            pass

    assert error.value.code == 4404


def test_created_session_is_closed_with_4409() -> None:
    session_id = create_session(start=False)

    with pytest.raises(WebSocketDisconnect) as error:
        with client.websocket_connect(f"/ws/v1/sessions/{session_id}"):
            pass

    assert error.value.code == 4409


def test_websocket_unsubscribes_on_disconnect() -> None:
    session_id = create_session()
    parsed_session_id = UUID(session_id)
    broker = get_session_broker()

    with client.websocket_connect(
        f"/ws/v1/sessions/{session_id}"
    ) as websocket:
        websocket.receive_json()
        assert broker.subscriber_count(parsed_session_id) == 1

    assert broker.subscriber_count(parsed_session_id) == 0
