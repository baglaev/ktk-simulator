from __future__ import annotations

from dataclasses import dataclass
from hmac import compare_digest

from app.config import Settings
from app.domain.enums import AuthRole


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    username: str
    role: AuthRole
    redirect_to: str


class SimpleAuthenticationService:
    """Validate the two configurable educational demo accounts.

    This intentionally does not issue a token or create a server-side session.
    It is suitable only for the current demonstration frontend flow.
    """

    def __init__(self, settings: Settings) -> None:
        self._accounts = (
            (
                settings.auth_user_login,
                settings.auth_user_password.get_secret_value(),
                AuthRole.USER,
                settings.auth_user_redirect_to,
            ),
            (
                settings.auth_instructor_login,
                settings.auth_instructor_password.get_secret_value(),
                AuthRole.INSTRUCTOR,
                settings.auth_instructor_redirect_to,
            ),
        )

    def authenticate(
        self,
        login: str,
        password: str,
    ) -> AuthenticatedPrincipal | None:
        matched: AuthenticatedPrincipal | None = None
        for expected_login, expected_password, role, redirect_to in self._accounts:
            login_matches = compare_digest(login, expected_login)
            password_matches = compare_digest(password, expected_password)
            if login_matches and password_matches:
                matched = AuthenticatedPrincipal(
                    username=expected_login,
                    role=role,
                    redirect_to=redirect_to,
                )
        return matched
