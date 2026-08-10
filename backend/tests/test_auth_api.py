from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_user_login_returns_main_page() -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"login": "user", "password": "user"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "login": True,
        "role": "user",
        "redirectTo": "/",
    }


def test_instructor_login_returns_instructor_page() -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"login": "instructor", "password": "instructor"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "login": True,
        "role": "instructor",
        "redirectTo": "/instructor",
    }


def test_wrong_password_returns_stable_unauthorized_response() -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"login": "user", "password": "wrong"},
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
        json={"login": "User", "password": "user"},
    )

    assert response.status_code == 401
    assert response.json()["login"] is False


def test_password_with_extra_spaces_is_rejected() -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"login": "user", "password": " user "},
    )

    assert response.status_code == 401
    assert response.json()["login"] is False


def test_missing_password_is_validation_error() -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"login": "user"},
    )

    assert response.status_code == 422


def test_extra_credentials_fields_are_rejected() -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"login": "user", "password": "user", "role": "instructor"},
    )

    assert response.status_code == 422
