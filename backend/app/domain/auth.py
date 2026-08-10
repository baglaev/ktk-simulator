from __future__ import annotations

from typing import Literal

from pydantic import ConfigDict, Field

from app.domain.base import APIModel
from app.domain.enums import AuthRole


class LoginRequest(APIModel):
    """Credentials received from the frontend login form."""

    model_config = ConfigDict(str_strip_whitespace=False)

    login: str = Field(max_length=128)
    password: str = Field(max_length=128)


class LoginSuccessResponse(APIModel):
    """Successful demo authentication result used for frontend routing."""

    login: Literal[True] = True
    role: AuthRole
    redirect_to: str = Field(min_length=1)


class LoginFailureResponse(APIModel):
    """Stable response body for an invalid login or password."""

    login: Literal[False] = False
    error: str = Field(min_length=1)
