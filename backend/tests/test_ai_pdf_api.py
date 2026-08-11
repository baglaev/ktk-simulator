from fastapi.testclient import TestClient

from app.api.dependencies import get_session_manager
from app.domain import CreateSessionRequest, TrainingMode
from app.main import app
from app.services import SessionManager


def test_download_generated_ai_analysis_as_pdf(monkeypatch) -> None:
    monkeypatch.setenv("AI_LLM_ENABLED", "false")
    manager = SessionManager()
    created = manager.create_session(
        CreateSessionRequest(
            scenario_id="MVP-SC-01",
            trainee_id="pdf-test-trainee",
            mode=TrainingMode.TRAINING,
        )
    )
    manager.start_session(created.session_id)
    manager.advance_session(created.session_id, 120_000)
    manager.generate_ai_analysis(created.session_id)
    app.dependency_overrides[get_session_manager] = lambda: manager

    try:
        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/sessions/{created.session_id}"
                "/ai-analysis/report.pdf"
            )
    finally:
        app.dependency_overrides.pop(get_session_manager, None)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"] == (
        "attachment; filename="
        f'"ktk-elou-avt-ai-report-{created.session_id}.pdf"'
    )
    assert response.content.startswith(b"%PDF-")
    assert len(response.content) > 10_000


def test_pdf_requires_previously_generated_ai_analysis() -> None:
    manager = SessionManager()
    created = manager.create_session(
        CreateSessionRequest(
            scenario_id="MVP-SC-01",
            trainee_id="pdf-test-trainee",
            mode=TrainingMode.CONTROL,
        )
    )
    manager.start_session(created.session_id)
    manager.complete_session(created.session_id)
    app.dependency_overrides[get_session_manager] = lambda: manager

    try:
        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/sessions/{created.session_id}"
                "/ai-analysis/report.pdf"
            )
    finally:
        app.dependency_overrides.pop(get_session_manager, None)

    assert response.status_code == 409
    assert response.json() == {
        "detail": "AI analysis has not been generated; call POST ai-analysis"
    }
