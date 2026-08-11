from fastapi.testclient import TestClient

from app.api.dependencies import get_session_manager
from app.domain import CreateSessionRequest, TrainingMode
from app.main import app
from app.persistence import SessionRepository, create_database
from app.services import SessionManager


def build_manager() -> SessionManager:
    _, factory = create_database("sqlite+pysqlite:///:memory:")
    return SessionManager(repository=SessionRepository(factory))


def complete_attempt(
    manager: SessionManager,
    *,
    trainee_id: str,
    instructor_id: str,
    mode: TrainingMode,
) -> str:
    session = manager.create_session(
        CreateSessionRequest(
            scenario_id="MVP-SC-01",
            trainee_id=trainee_id,
            instructor_id=instructor_id,
            mode=mode,
        )
    )
    manager.start_session(session.session_id)
    manager.complete_session(session.session_id)
    return str(session.session_id)


def test_instructor_can_list_completed_trainee_results() -> None:
    manager = build_manager()
    first_id = complete_attempt(
        manager,
        trainee_id="trainee-001",
        instructor_id="instructor-001",
        mode=TrainingMode.TRAINING,
    )
    second_id = complete_attempt(
        manager,
        trainee_id="trainee-002",
        instructor_id="instructor-001",
        mode=TrainingMode.CONTROL,
    )
    manager.create_session(
        CreateSessionRequest(
            scenario_id="MVP-SC-01",
            trainee_id="unfinished-trainee",
            instructor_id="instructor-001",
            mode=TrainingMode.TRAINING,
        )
    )
    app.dependency_overrides[get_session_manager] = lambda: manager
    try:
        response = TestClient(app).get("/api/v1/instructor/results")
    finally:
        app.dependency_overrides.pop(get_session_manager, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert payload["limit"] == 100
    assert payload["offset"] == 0
    assert {item["sessionId"] for item in payload["items"]} == {
        first_id,
        second_id,
    }
    assert all(item["sessionStatus"] == "failed" for item in payload["items"])
    assert all(type(item["totalScore"]) is int for item in payload["items"])
    assert all(item["completedAt"] for item in payload["items"])


def test_instructor_results_support_filters_and_pagination() -> None:
    manager = build_manager()
    expected_id = complete_attempt(
        manager,
        trainee_id="trainee-filtered",
        instructor_id="instructor-001",
        mode=TrainingMode.CONTROL,
    )
    complete_attempt(
        manager,
        trainee_id="trainee-other",
        instructor_id="instructor-002",
        mode=TrainingMode.TRAINING,
    )
    app.dependency_overrides[get_session_manager] = lambda: manager
    try:
        client = TestClient(app)
        response = client.get(
            "/api/v1/instructor/results",
            params={
                "traineeId": "trainee-filtered",
                "instructorId": "instructor-001",
                "mode": "control",
                "limit": 1,
                "offset": 0,
            },
        )
    finally:
        app.dependency_overrides.pop(get_session_manager, None)

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["sessionId"] == expected_id


def test_instructor_results_returns_empty_page_before_completion() -> None:
    manager = build_manager()
    manager.create_session(
        CreateSessionRequest(
            scenario_id="MVP-SC-01",
            trainee_id="trainee-001",
            mode=TrainingMode.TRAINING,
        )
    )
    app.dependency_overrides[get_session_manager] = lambda: manager
    try:
        response = TestClient(app).get("/api/v1/instructor/results")
    finally:
        app.dependency_overrides.pop(get_session_manager, None)

    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "total": 0,
        "limit": 100,
        "offset": 0,
    }
