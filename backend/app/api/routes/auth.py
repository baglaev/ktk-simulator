from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from app.domain import (
    LoginFailureResponse,
    LoginRequest,
    LoginSuccessResponse,
)
from app.services import SimpleAuthenticationService
from app.api.dependencies import get_session_repository
from app.persistence import SessionRepository


router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def get_authentication_service(
    repository: Annotated[
        SessionRepository,
        Depends(get_session_repository),
    ],
) -> SimpleAuthenticationService:
    return SimpleAuthenticationService(repository)


@router.post(
    "/login",
    response_model=LoginSuccessResponse,
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": LoginFailureResponse,
            "description": "Неверный логин или пароль",
        }
    },
    summary="Вход обучаемого или инструктора",
)
async def login(
    credentials: LoginRequest,
    service: Annotated[
        SimpleAuthenticationService,
        Depends(get_authentication_service),
    ],
) -> LoginSuccessResponse | JSONResponse:
    principal = service.authenticate(
        credentials.login,
        credentials.password,
    )
    if principal is None:
        failure = LoginFailureResponse(
            error="Неверный логин или пароль",
        )
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=failure.model_dump(by_alias=True),
        )
    return LoginSuccessResponse(
        role=principal.role,
        username=principal.username,
        display_name=principal.display_name,
        assigned_instructor_id=principal.assigned_instructor_id,
        redirect_to=principal.redirect_to,
    )
