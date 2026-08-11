from __future__ import annotations

from dataclasses import dataclass

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.domain.enums import AuthRole
from app.persistence import SessionRepository


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    username: str
    display_name: str
    role: AuthRole
    assigned_instructor_id: str | None
    redirect_to: str


class SimpleAuthenticationService:
    """Validate database-backed educational accounts.

    This intentionally does not issue a token or create a server-side session.
    It is suitable only for the current demonstration frontend flow.
    """

    _DUMMY_PASSWORD_HASH = (
        "$argon2id$v=19$m=65536,t=3,p=4$JOomL9mbRXxPgurMdde0OA$"
        "ENLrI6I/fVrmEn+G791vxhLSAGSvI9iaZHmwdRWIhIA"
    )

    def __init__(self, repository: SessionRepository) -> None:
        self._repository = repository
        self._password_hasher = PasswordHasher()

    def authenticate(
        self,
        login: str,
        password: str,
    ) -> AuthenticatedPrincipal | None:
        account = self._repository.get_user_account(login)
        password_hash = (
            account.password_hash
            if account is not None
            else self._DUMMY_PASSWORD_HASH
        )
        try:
            password_matches = self._password_hasher.verify(
                password_hash,
                password,
            )
        except (InvalidHashError, VerificationError):
            password_matches = False

        if account is None or not account.is_active or not password_matches:
            return None

        role = AuthRole(account.role)
        return AuthenticatedPrincipal(
            username=account.login,
            display_name=account.full_name,
            role=role,
            assigned_instructor_id=account.assigned_instructor_id,
            redirect_to="/instructor" if role is AuthRole.INSTRUCTOR else "/",
        )
