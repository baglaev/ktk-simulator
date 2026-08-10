from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_session_manager
from app.domain import (
    AdvanceSessionRequest,
    CreateSessionRequest,
    ModelSnapshot,
    RecordedAction,
    SessionResult,
    TrainingSession,
)
from app.services import SessionManager


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


@router.get("/{session_id}/result", response_model=SessionResult)
async def get_result(
    session_id: UUID,
    manager: SessionManager = Depends(get_session_manager),
) -> SessionResult:
    """Return the deterministic SCR-04 result after terminal completion."""

    return manager.get_result(session_id)
