from fastapi.testclient import TestClient

from app.api.dependencies import get_session_manager
from app.domain import (
    ActionType,
    CreateSessionRequest,
    ScenarioActionRequest,
    TrainingMode,
)
from app.main import app
from app.persistence import SessionRepository, create_database
from app.services import SessionManager


def build_manager() -> SessionManager:
    _, factory = create_database("sqlite+pysqlite:///:memory:")
    repository = SessionRepository(factory)
    repository.save_user_account(
        login="Ivanov.II",
        password_hash="not-used-by-dashboard-tests",
        role="user",
        full_name="Иванов И. И.",
        assigned_instructor_id="Petrov.PP",
    )
    return SessionManager(repository=repository)


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
    assert "limit" not in payload
    assert "offset" not in payload
    assert {item["sessionId"] for item in payload["items"]} == {
        first_id,
        second_id,
    }
    assert all(item["sessionStatus"] == "failed" for item in payload["items"])
    assert all(type(item["totalScore"]) is int for item in payload["items"])
    assert all(item["completedAt"] for item in payload["items"])
    assert all(
        item["traineeName"] == item["traineeId"]
        for item in payload["items"]
    )
    assert all(
        all(entry["kind"] in {"action", "hint"} for entry in item["journal"])
        for item in payload["items"]
    )
    control_item = next(
        item for item in payload["items"] if item["mode"] == "control"
    )
    assert control_item["journal"] == []


def test_instructor_results_include_full_name_and_journal() -> None:
    manager = build_manager()
    trainee_id = "Ivanov.II"
    session = manager.create_session(
        CreateSessionRequest(
            scenario_id="MVP-SC-01",
            trainee_id=trainee_id,
            instructor_id="Petrov.PP",
            mode=TrainingMode.TRAINING,
        )
    )
    manager.start_session(session.session_id)
    manager.apply_scenario_action(
        session.session_id,
        ScenarioActionRequest(
            action_type=ActionType.VIEW_SIGNAL,
            target_id="PRA351",
        ),
    )
    manager.complete_session(session.session_id)
    app.dependency_overrides[get_session_manager] = lambda: manager
    try:
        response = TestClient(app).get("/api/v1/instructor/results")
    finally:
        app.dependency_overrides.pop(get_session_manager, None)

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["traineeName"] == "Иванов И. И."
    assert item["journal"][0] == {
        "time": "00:00",
        "virtualTimeMs": 0,
        "kind": "action",
        "description": "Просмотрен параметр PRA 351",
    }


def test_selected_trainee_results_support_mode_and_pagination() -> None:
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
            "/api/v1/instructor/trainees/trainee-filtered/results",
            params={
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
    assert response.json() == {"items": [], "total": 0}


def test_all_results_openapi_has_no_query_parameters() -> None:
    operation = app.openapi()["paths"]["/api/v1/instructor/results"]["get"]
    assert operation.get("parameters", []) == []


def test_instructor_receives_full_trainee_directory_before_attempts() -> None:
    manager = build_manager()
    app.dependency_overrides[get_session_manager] = lambda: manager
    try:
        response = TestClient(app).get("/api/v1/instructor/trainees")
    finally:
        app.dependency_overrides.pop(get_session_manager, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert len(payload["items"]) == 1
    assert {item["traineeId"] for item in payload["items"]} == {
        "Ivanov.II"
    }
    assert all(item["attemptsCount"] == 0 for item in payload["items"])
    assert "password" not in response.text.lower()


def test_trainee_directory_is_enriched_from_persisted_results() -> None:
    manager = build_manager()
    trainee_id = "Ivanov.II"
    session = manager.create_session(
        CreateSessionRequest(
            scenario_id="MVP-SC-01",
            trainee_id=trainee_id,
            instructor_id="Petrov.PP",
            mode=TrainingMode.TRAINING,
        )
    )
    manager.start_session(session.session_id)
    manager.apply_scenario_action(
        session.session_id,
        ScenarioActionRequest(
            action_type=ActionType.VIEW_SIGNAL,
            target_id="PRA351",
        ),
    )
    manager.complete_session(session.session_id)
    session_id = str(session.session_id)
    app.dependency_overrides[get_session_manager] = lambda: manager
    try:
        client = TestClient(app)
        profile_response = client.get(
            f"/api/v1/instructor/trainees/{trainee_id}"
        )
        history_response = client.get(
            f"/api/v1/instructor/trainees/{trainee_id}/results"
        )
        result_response = client.get(
            f"/api/v1/instructor/trainees/{trainee_id}/results/{session_id}"
        )
        journal_response = client.get(
            f"/api/v1/instructor/trainees/{trainee_id}/results/"
            f"{session_id}/journal"
        )
        overview_response = client.get("/api/v1/instructor/overview")
    finally:
        app.dependency_overrides.pop(get_session_manager, None)

    assert profile_response.status_code == 200
    profile = profile_response.json()
    assert profile["fullName"] == "Иванов И. И."
    assert profile["assignedInstructorId"] == "Petrov.PP"
    assert profile["attemptsCount"] == 1
    assert type(profile["averageScore"]) is int
    assert type(profile["bestScore"]) is int
    assert profile["latestResult"]["sessionId"] == session_id
    assert profile["latestResult"]["mode"] == "training"
    assert profile["latestResult"]["resultStatus"] == "failed"

    assert history_response.status_code == 200
    assert history_response.json()["total"] == 1
    assert history_response.json()["items"][0]["sessionId"] == session_id

    assert result_response.status_code == 200
    assert result_response.json()["sessionId"] == session_id

    assert journal_response.status_code == 200
    journal = journal_response.json()
    assert journal["traineeId"] == trainee_id
    assert journal["mode"] == "training"
    assert journal["items"][0]["kind"] == "action"
    assert journal["items"][0]["time"] == "00:00"
    assert "PRA 351" in journal["items"][0]["description"]

    assert overview_response.status_code == 200
    overview = overview_response.json()
    assert overview["totalTrainees"] == 1
    assert overview["traineesWithAttempts"] == 1
    assert overview["completedAttempts"] == 1


def test_instructor_result_detail_checks_trainee_ownership() -> None:
    manager = build_manager()
    session_id = complete_attempt(
        manager,
        trainee_id="trainee-owner",
        instructor_id="instructor",
        mode=TrainingMode.TRAINING,
    )
    app.dependency_overrides[get_session_manager] = lambda: manager
    try:
        response = TestClient(app).get(
            "/api/v1/instructor/trainees/another-trainee/"
            f"results/{session_id}"
        )
    finally:
        app.dependency_overrides.pop(get_session_manager, None)

    assert response.status_code == 404
