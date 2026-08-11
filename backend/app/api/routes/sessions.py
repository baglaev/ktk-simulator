from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api.dependencies import get_session_manager
from app.domain import (
    AdvanceSessionRequest,
    AdaptiveRepetitionPlan,
    AssistantQuestionRequest,
    CreateSessionRequest,
    ModelSnapshot,
    RecordedAction,
    ScenarioHintMessage,
    SessionResult,
    SessionAIAnalysis,
    TrainingSession,
)
from app.services import RAGUnavailableError, SessionManager
from app.services.pdf_report import SessionAIAnalysisPDFBuilder


router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])


@router.post(
    "",
    response_model=TrainingSession,
    status_code=status.HTTP_201_CREATED,
)
async def create_session(
    request: CreateSessionRequest,
    manager: SessionManager = Depends(get_session_manager),
) -> TrainingSession:
    return manager.create_session(request)


@router.get("/{session_id}", response_model=TrainingSession)
async def get_session(
    session_id: UUID,
    manager: SessionManager = Depends(get_session_manager),
) -> TrainingSession:
    return manager.get_session(session_id)


@router.post("/{session_id}/start", response_model=TrainingSession)
async def start_session(
    session_id: UUID,
    manager: SessionManager = Depends(get_session_manager),
) -> TrainingSession:
    return manager.start_session(session_id)


@router.post("/{session_id}/pause", response_model=TrainingSession)
async def pause_session(
    session_id: UUID,
    manager: SessionManager = Depends(get_session_manager),
) -> TrainingSession:
    return manager.pause_session(session_id)


@router.post("/{session_id}/resume", response_model=TrainingSession)
async def resume_session(
    session_id: UUID,
    manager: SessionManager = Depends(get_session_manager),
) -> TrainingSession:
    return manager.resume_session(session_id)


@router.post("/{session_id}/complete", response_model=TrainingSession)
async def complete_session(
    session_id: UUID,
    manager: SessionManager = Depends(get_session_manager),
) -> TrainingSession:
    return manager.complete_session(session_id)


@router.post("/{session_id}/advance", response_model=ModelSnapshot)
async def advance_session(
    session_id: UUID,
    request: AdvanceSessionRequest,
    manager: SessionManager = Depends(get_session_manager),
) -> ModelSnapshot:
    return manager.advance_session(session_id, request.dt_ms)


@router.get("/{session_id}/snapshot", response_model=ModelSnapshot)
async def get_snapshot(
    session_id: UUID,
    manager: SessionManager = Depends(get_session_manager),
) -> ModelSnapshot:
    return manager.get_snapshot(session_id)


@router.get("/{session_id}/actions", response_model=list[RecordedAction])
async def list_actions(
    session_id: UUID,
    manager: SessionManager = Depends(get_session_manager),
) -> list[RecordedAction]:
    """Return the persisted action audit ordered by model sequence."""

    return manager.list_actions(session_id)


@router.get("/{session_id}/hints", response_model=list[ScenarioHintMessage])
async def list_hints(
    session_id: UUID,
    manager: SessionManager = Depends(get_session_manager),
) -> list[ScenarioHintMessage]:
    """Return hints actually shown during a training-mode session."""

    return manager.list_hints(session_id)


@router.get("/{session_id}/result", response_model=SessionResult)
async def get_result(
    session_id: UUID,
    manager: SessionManager = Depends(get_session_manager),
) -> SessionResult:
    """Return the deterministic SCR-04 result after terminal completion."""

    return manager.get_result(session_id)


@router.post("/{session_id}/ai-analysis", response_model=SessionAIAnalysis)
def generate_ai_analysis(
    session_id: UUID,
    manager: SessionManager = Depends(get_session_manager),
) -> SessionAIAnalysis:
    """Build and persist SCR-05 explanation without changing SCR-04 score."""

    return manager.generate_ai_analysis(session_id)


@router.get("/{session_id}/ai-analysis", response_model=SessionAIAnalysis)
async def get_ai_analysis(
    session_id: UUID,
    manager: SessionManager = Depends(get_session_manager),
) -> SessionAIAnalysis:
    return manager.get_ai_analysis(session_id)


@router.get(
    "/{session_id}/ai-analysis/report.pdf",
    response_class=Response,
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "Скачиваемый итоговый ИИ-отчет в формате PDF",
        }
    },
)
def download_ai_analysis_pdf(
    session_id: UUID,
    manager: SessionManager = Depends(get_session_manager),
) -> Response:
    """Render an already generated post-session analysis as a PDF file."""

    analysis = manager.get_ai_analysis(session_id)
    content = SessionAIAnalysisPDFBuilder().build(analysis)
    return Response(
        content=content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                "attachment; filename="
                f'"ktk-elou-avt-ai-report-{session_id}.pdf"'
            )
        },
    )
@router.get(
    "/{session_id}/adaptive-plan",
    response_model=AdaptiveRepetitionPlan,
)
async def get_adaptive_plan(
    session_id: UUID,
    manager: SessionManager = Depends(get_session_manager),
) -> AdaptiveRepetitionPlan:
    return manager.get_adaptive_plan(session_id)


@router.post("/{session_id}/assistant/question")
def ask_post_session_assistant(
    session_id: UUID,
    request: AssistantQuestionRequest,
    manager: SessionManager = Depends(get_session_manager),
) -> dict:
    """Grounded RAG Q&A; deliberately unavailable during an active attempt."""

    try:
        return manager.ask_post_session_assistant(session_id, request.question)
    except RAGUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error
