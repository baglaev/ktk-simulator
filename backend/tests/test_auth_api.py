import re

from fastapi.testclient import TestClient

from app.main import app
from app.services.demo_corporate_accounts import DEMO_CORPORATE_ACCOUNTS


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


def test_twenty_demo_corporate_accounts_follow_password_policy() -> None:
    assert len(DEMO_CORPORATE_ACCOUNTS) == 20
    assert len({login for login, _password in DEMO_CORPORATE_ACCOUNTS}) == 20
    assert all(
        len(password) >= 12
        for _login, password in DEMO_CORPORATE_ACCOUNTS
    )
    corporate_login = re.compile(
        r"^[A-Z][A-Za-z]+\.[A-Z]{2}@gazprom-neft\.ru$"
    )
    assert all(
        corporate_login.fullmatch(login)
        for login, _password in DEMO_CORPORATE_ACCOUNTS
    )


def test_example_corporate_accounts_login_as_users() -> None:
    for login, password in DEMO_CORPORATE_ACCOUNTS[:2]:
        response = client.post(
            "/api/v1/auth/login",
            json={"login": login, "password": password},
        )

        assert response.status_code == 200
        assert response.json() == {
            "login": True,
            "role": "user",
            "redirectTo": "/",
        }


def test_every_demo_corporate_account_can_login() -> None:
    for login, password in DEMO_CORPORATE_ACCOUNTS:
        response = client.post(
            "/api/v1/auth/login",
            json={"login": login, "password": password},
        )
        assert response.status_code == 200
        assert response.json()["role"] == "user"


def test_corporate_account_rejects_wrong_password() -> None:
    login, _password = DEMO_CORPORATE_ACCOUNTS[0]
    response = client.post(
        "/api/v1/auth/login",
        json={"login": login, "password": "WrongPassword#2026"},
    )

    assert response.status_code == 401
    assert response.json()["login"] is False
