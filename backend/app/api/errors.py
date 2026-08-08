from fastapi import Request, status
from fastapi.responses import JSONResponse

from app.services import (
    InvalidSessionTransitionError,
    SessionConflictError,
    SessionNotFoundError,
)


async def session_not_found_handler(
    _: Request,
    error: SessionNotFoundError,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": str(error)},
    )


async def invalid_session_transition_handler(
    _: Request,
    error: InvalidSessionTransitionError,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": str(error)},
    )


async def session_conflict_handler(
    _: Request,
    error: SessionConflictError,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": str(error)},
    )
