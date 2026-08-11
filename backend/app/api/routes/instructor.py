from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.api.dependencies import get_session_manager
from app.domain import (
    InstructorAttemptJournal,
    InstructorJournalItem,
    InstructorOverview,
    InstructorResultsCollection,
    InstructorTrainee,
    InstructorTraineeList,
    SessionResult,
    TraineeResultsPage,
    TrainingMode,
)
from app.services import InstructorDashboardService, SessionManager


router = APIRouter(prefix="/api/v1/instructor", tags=["instructor"])


def _dashboard(
    request: Request,
    manager: SessionManager,
) -> InstructorDashboardService:
    return InstructorDashboardService(manager, request.app.state.settings)


@router.get(
    "/overview",
    response_model=InstructorOverview,
    summary="Сводка страницы инструктора",
)
async def get_instructor_overview(
    request: Request,
    manager: SessionManager = Depends(get_session_manager),
) -> InstructorOverview:
    return _dashboard(request, manager).get_overview()


@router.get(
    "/trainees",
    response_model=InstructorTraineeList,
    summary="Полный список обучаемых",
)
async def list_trainees(
    request: Request,
    manager: SessionManager = Depends(get_session_manager),
) -> InstructorTraineeList:
    return _dashboard(request, manager).list_trainees()


@router.get(
    "/trainees/{trainee_id}",
    response_model=InstructorTrainee,
    summary="Карточка обучаемого",
)
async def get_trainee(
    trainee_id: str,
    request: Request,
    manager: SessionManager = Depends(get_session_manager),
) -> InstructorTrainee:
    trainee = _dashboard(request, manager).get_trainee(trainee_id)
    if trainee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"trainee '{trainee_id}' was not found",
        )
    return trainee


@router.get(
    "/trainees/{trainee_id}/results",
    response_model=TraineeResultsPage,
    summary="История попыток обучаемого",
)
async def list_selected_trainee_results(
    trainee_id: str,
    mode: TrainingMode | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
    manager: SessionManager = Depends(get_session_manager),
) -> TraineeResultsPage:
    return manager.list_trainee_results(
        trainee_id=trainee_id,
        mode=mode,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/trainees/{trainee_id}/results/{session_id}",
    response_model=SessionResult,
    summary="Полный результат попытки обучаемого",
)
async def get_selected_trainee_result(
    trainee_id: str,
    session_id: UUID,
    manager: SessionManager = Depends(get_session_manager),
) -> SessionResult:
    session = manager.get_session(session_id)
    if session.trainee_id != trainee_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="result was not found for this trainee",
        )
    return manager.get_result(session_id)


@router.get(
    "/trainees/{trainee_id}/results/{session_id}/journal",
    response_model=InstructorAttemptJournal,
    summary="Журнал попытки обучаемого",
)
async def get_selected_trainee_journal(
    trainee_id: str,
    session_id: UUID,
    manager: SessionManager = Depends(get_session_manager),
) -> InstructorAttemptJournal:
    session = manager.get_session(session_id)
    if session.trainee_id != trainee_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="journal was not found for this trainee",
        )

    entries = [
        InstructorJournalItem(
            time=_format_virtual_time(item.virtual_time_ms),
            virtual_time_ms=item.virtual_time_ms,
            kind="action",
            description=item.description,
        )
        for item in manager.list_actions(session_id)
    ]
    entries.extend(
        InstructorJournalItem(
            time=_format_virtual_time(item.virtual_time_ms),
            virtual_time_ms=item.virtual_time_ms,
            kind="hint",
            description=f"ИИ-подсказка: {item.title}. {item.message}",
        )
        for item in manager.list_hints(session_id)
    )
    entries.sort(key=lambda item: (item.virtual_time_ms, item.kind))
    return InstructorAttemptJournal(
        session_id=session_id,
        trainee_id=trainee_id,
        mode=session.mode,
        items=entries,
    )


def _format_virtual_time(value_ms: int) -> str:
    minutes, seconds = divmod(value_ms // 1_000, 60)
    return f"{minutes:02d}:{seconds:02d}"


@router.get(
    "/results",
    response_model=InstructorResultsCollection,
    summary="Результаты обучаемых",
)
async def list_trainee_results(
    request: Request,
    manager: SessionManager = Depends(get_session_manager),
) -> InstructorResultsCollection:
    """Return all completed attempts without required query parameters."""

    return _dashboard(request, manager).list_results()
