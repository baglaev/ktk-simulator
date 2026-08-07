from fastapi import FastAPI
from pydantic import BaseModel

from app.api.routes import scenarios_router
from app.config import get_settings


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

    return application


app = create_app()
