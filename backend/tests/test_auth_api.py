from fastapi.testclient import TestClient

from app.api.dependencies import get_session_repository
from app.main import app


client = TestClient(app)


def test_trainee_login_returns_main_page() -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"login": "Ivanov.II", "password": "user"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "login": True,
        "role": "user",
        "username": "Ivanov.II",
        "displayName": "Иванов И. И.",
        "assignedInstructorId": "Petrov.PP",
        "redirectTo": "/",
    }


def test_instructor_login_returns_instructor_page() -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"login": "Petrov.PP", "password": "instructor"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "login": True,
        "role": "instructor",
        "username": "Petrov.PP",
        "displayName": "Петров П. П.",
        "assignedInstructorId": None,
        "redirectTo": "/instructor",
    }


def test_passwords_are_stored_only_as_argon2_hashes() -> None:
    repository = get_session_repository()

    for login in ("Ivanov.II", "Petrov.PP"):
        account = repository.get_user_account(login)
        assert account is not None
        assert account.password_hash.startswith("$argon2id$")
        assert account.password_hash not in {"user", "instructor"}


def test_wrong_password_returns_stable_unauthorized_response() -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"login": "Ivanov.II", "password": "wrong"},
    )

    assert response.status_code == 401
    assert response.json() == {
        "login": False,
        "error": "Неверный логин или пароль",
    }


def test_unknown_login_does_not_reveal_existing_accounts() -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"login": "unknown", "password": "unknown"},
    )

    assert response.status_code == 401
    assert response.json() == {
        "login": False,
        "error": "Неверный логин или пароль",
    }


def test_login_is_case_sensitive() -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"login": "ivanov.ii", "password": "user"},
    )

    assert response.status_code == 401
    assert response.json()["login"] is False


def test_password_with_extra_spaces_is_rejected() -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"login": "Ivanov.II", "password": " user "},
    )

    assert response.status_code == 401
    assert response.json()["login"] is False


def test_old_hardcoded_accounts_are_not_available() -> None:
    for login, password in (("user", "user"), ("instructor", "instructor")):
        response = client.post(
            "/api/v1/auth/login",
            json={"login": login, "password": password},
        )
        assert response.status_code == 401


def test_missing_password_is_validation_error() -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"login": "Ivanov.II"},
    )

    assert response.status_code == 422


def test_extra_credentials_fields_are_rejected() -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={
            "login": "Ivanov.II",
            "password": "user",
            "role": "instructor",
        },
    )

    assert response.status_code == 422
