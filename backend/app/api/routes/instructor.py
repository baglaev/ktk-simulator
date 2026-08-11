from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_session_manager
from app.domain import TraineeResultsPage, TrainingMode
from app.services import SessionManager


router = APIRouter(prefix="/api/v1/instructor", tags=["instructor"])


@router.get(
    "/results",
    response_model=TraineeResultsPage,
    summary="Результаты обучаемых",
)
async def list_trainee_results(
    trainee_id: Annotated[
        str | None,
        Query(alias="traineeId", min_length=1),
    ] = None,
    instructor_id: Annotated[
        str | None,
        Query(alias="instructorId", min_length=1),
    ] = None,
    mode: TrainingMode | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
    manager: SessionManager = Depends(get_session_manager),
) -> TraineeResultsPage:
    """List only attempts that already have a deterministic result."""

    return manager.list_trainee_results(
        trainee_id=trainee_id,
        instructor_id=instructor_id,
        mode=mode,
        limit=limit,
        offset=offset,
    )
