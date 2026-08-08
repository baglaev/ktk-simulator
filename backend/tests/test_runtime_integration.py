import time

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.api.dependencies import get_session_broker, get_session_manager
from app.config import Settings
from app.main import create_app


@pytest.fixture(autouse=True)
def reset_backend_state():
    get_session_manager.cache_clear()
    get_session_broker.cache_clear()
    yield
    get_session_manager.cache_clear()
    get_session_broker.cache_clear()


def runtime_settings(**overrides) -> Settings:
    return Settings(
        simulation_tick_interval_ms=20,
        simulation_step_ms=1_000,
        cors_allowed_origins=["http://localhost:5173"],
        **overrides,
    )


def create_session(client: TestClient) -> str:
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
    started = client.post(f"/api/v1/sessions/{session_id}/start")
    assert started.status_code == 200
    return session_id


def test_started_session_streams_deltas_without_manual_advance() -> None:
    application = create_app(runtime_settings())

    with TestClient(application) as client:
        session_id = create_session(client)
        with client.websocket_connect(
            f"/ws/v1/sessions/{session_id}"
        ) as websocket:
            snapshot = websocket.receive_json()
            delta = websocket.receive_json()

    assert snapshot["type"] == "telemetry.snapshot"
    assert delta["type"] == "telemetry.delta"
    assert delta["sequenceNo"] > snapshot["sequenceNo"]
    assert delta["stateVersion"] > snapshot["stateVersion"]
    assert delta["virtualTimeMs"] > snapshot["virtualTimeMs"]


def test_pause_freezes_and_resume_continues_virtual_time() -> None:
    application = create_app(runtime_settings())

    with TestClient(application) as client:
        session_id = create_session(client)
        time.sleep(0.05)
        paused = client.post(f"/api/v1/sessions/{session_id}/pause")
        paused_at = paused.json()["virtualTimeMs"]

        time.sleep(0.06)
        still_paused = client.get(f"/api/v1/sessions/{session_id}").json()
        assert still_paused["virtualTimeMs"] == paused_at

        resumed = client.post(f"/api/v1/sessions/{session_id}/resume")
        assert resumed.status_code == 200
        time.sleep(0.05)
        running = client.get(f"/api/v1/sessions/{session_id}").json()
        assert running["virtualTimeMs"] > paused_at


def test_lifespan_stops_runtime() -> None:
    application = create_app(runtime_settings())

    with TestClient(application):
        runtime = application.state.simulation_runtime
        assert runtime.is_running

    assert not runtime.is_running


def test_cors_allows_configured_frontend_origin() -> None:
    application = create_app(
        runtime_settings(simulation_auto_run=False)
    )

    with TestClient(application) as client:
        response = client.options(
            "/api/v1/sessions",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == (
        "http://localhost:5173"
    )


def test_cors_does_not_allow_unknown_origin() -> None:
    application = create_app(
        runtime_settings(simulation_auto_run=False)
    )

    with TestClient(application) as client:
        response = client.options(
            "/api/v1/sessions",
            headers={
                "Origin": "https://untrusted.example",
                "Access-Control-Request-Method": "POST",
            },
        )

    assert "access-control-allow-origin" not in response.headers


def test_websocket_rejects_unknown_browser_origin() -> None:
    application = create_app(
        runtime_settings(simulation_auto_run=False)
    )

    with TestClient(application) as client:
        with pytest.raises(WebSocketDisconnect) as error:
            with client.websocket_connect(
                "/ws/v1/sessions/99999999-9999-9999-9999-999999999999",
                headers={"Origin": "https://untrusted.example"},
            ):
                pass

    assert error.value.code == 4403
