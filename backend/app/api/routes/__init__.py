from app.api.routes.auth import router as auth_router
from app.api.routes.instructor import router as instructor_router
from app.api.routes.scenarios import router as scenarios_router
from app.api.routes.sessions import router as sessions_router
from app.api.routes.websocket import router as websocket_router

__all__ = [
    "auth_router",
    "instructor_router",
    "scenarios_router",
    "sessions_router",
    "websocket_router",
]
