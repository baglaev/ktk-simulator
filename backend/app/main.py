from fastapi import FastAPI
from pydantic import BaseModel

from app.api.errors import (
    invalid_session_transition_handler,
    session_conflict_handler,
    session_not_found_handler,
)
from app.api.routes import scenarios_router, sessions_router, websocket_router
from app.config import get_settings
from app.services import (
    InvalidSessionTransitionError,
    SessionConflictError,
    SessionNotFoundError,
)


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
    )

    @application.get(
        "/health",
        response_model=HealthResponse,
        tags=["system"],
        summary="Проверка работоспособности backend",
    )
    async def health() -> HealthResponse:
        return HealthResponse(
            status="ok",
            service=settings.app_name,
            version=settings.app_version,
        )

    application.include_router(scenarios_router)
    application.include_router(sessions_router)
    application.include_router(websocket_router)
    application.add_exception_handler(
        SessionNotFoundError,
        session_not_found_handler,
    )
    application.add_exception_handler(
        InvalidSessionTransitionError,
        invalid_session_transition_handler,
    )
    application.add_exception_handler(
        SessionConflictError,
        session_conflict_handler,
    )

    return application


app = create_app()
