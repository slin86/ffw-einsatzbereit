import pytest
from fastapi.testclient import TestClient

from tests.conftest import ADMIN, USER


def login(client: TestClient, name: str, password: str = USER[1]) -> int:
    r = client.post("/api/auth/login", json={"login": name, "password": password})
    return int(r.status_code)


@pytest.mark.parametrize("name", ["anwender", "Anwender", "  anwender  ", USER[0], USER[0].upper()])
def test_login_with_username_or_email(client: TestClient, name: str) -> None:
    assert login(client, name) == 200


@pytest.mark.parametrize("name", ["anwende", "anwender2", "anwender@example.org", ""])
def test_unknown_logins_are_rejected(client: TestClient, name: str) -> None:
    assert login(client, name) in (401, 422)


def test_wrong_password_with_username(client: TestClient) -> None:
    assert login(client, "anwender", "wrong-password") == 401


def test_username_is_visible_and_changeable(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    me = client.get("/api/me", headers=admin_headers).json()
    assert me["username"] == "admin"
    users = client.get("/api/users", headers=admin_headers).json()
    user = next(u for u in users if u["email"] == USER[0])

    renamed = client.patch(
        f"/api/users/{user['id']}", headers=admin_headers, json={"username": "Neuer_Name"}
    )
    assert renamed.status_code == 200 and renamed.json()["username"] == "neuer_name"
    assert login(client, "neuer_name") == 200
    assert login(client, "anwender") == 401

    taken = client.patch(
        f"/api/users/{user['id']}", headers=admin_headers, json={"username": "admin"}
    )
    assert taken.status_code == 409
    assert (
        client.patch(
            f"/api/users/{user['id']}", headers=admin_headers, json={"username": "ab"}
        ).status_code
        == 422
    )


def test_new_user_logs_in_with_username(client: TestClient, admin_headers: dict[str, str]) -> None:
    body = {
        "username": "Feuerwehr.Nils",
        "email": "nils@example.org",
        "display_name": "Nils",
        "password": "start-password-1",
    }
    created = client.post("/api/users", headers=admin_headers, json=body).json()
    assert created["username"] == "feuerwehr.nils"
    assert login(client, "feuerwehr.nils", "start-password-1") == 200
    assert login(client, ADMIN[0], ADMIN[1]) == 200
