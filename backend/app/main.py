from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.api.errors import (
    invalid_session_transition_handler,
    session_conflict_handler,
    session_not_found_handler,
)
from app.api.routes import (
    auth_router,
    scenarios_router,
    sessions_router,
    websocket_router,
)
from app.api.dependencies import get_session_manager
from app.config import Settings, get_settings
from app.services import (
    InvalidSessionTransitionError,
    SessionConflictError,
    SimulationRuntime,
    SessionNotFoundError,
)


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        runtime = SimulationRuntime(
            manager=get_session_manager(),
            tick_interval_ms=resolved_settings.simulation_tick_interval_ms,
        )
        application.state.simulation_runtime = runtime
        if resolved_settings.simulation_auto_run:
            await runtime.start()
        try:
            yield
        finally:
            await runtime.stop()

    application = FastAPI(
        title=resolved_settings.app_name,
        version=resolved_settings.app_version,
        lifespan=lifespan,
    )
    application.state.settings = resolved_settings
    application.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.cors_allowed_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
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
            service=resolved_settings.app_name,
            version=resolved_settings.app_version,
        )

    application.include_router(auth_router)
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
