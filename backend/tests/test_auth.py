import re

import pyotp
import pytest
from fastapi.testclient import TestClient

from tests.conftest import ADMIN, USER, login


def test_login_refresh_logout(client: TestClient) -> None:
    headers = login(client, USER)
    assert client.get("/api/me", headers=headers).json()["role"] == "user"
    assert "eb_refresh" in client.cookies

    old = client.cookies.get("eb_refresh")
    r = client.post("/api/auth/refresh")
    assert r.status_code == 200 and r.json()["access_token"]
    assert client.cookies.get("eb_refresh") != old

    new = client.cookies.get("eb_refresh")
    client.cookies.set("eb_refresh", old or "", path="/api/auth")
    assert client.post("/api/auth/refresh").status_code == 401
    client.cookies.set("eb_refresh", new or "", path="/api/auth")
    assert client.post("/api/auth/refresh").status_code == 401


def test_logout_revokes(client: TestClient) -> None:
    login(client, USER)
    token = client.cookies.get("eb_refresh")
    assert client.post("/api/auth/logout").status_code == 204
    client.cookies.set("eb_refresh", token or "", path="/api/auth")
    assert client.post("/api/auth/refresh").status_code == 401


def test_wrong_password_and_lockout(client: TestClient) -> None:
    for _ in range(5):
        r = client.post("/api/auth/login", json={"email": USER[0], "password": "wrong-password"})
        assert r.status_code == 401
    r = client.post("/api/auth/login", json={"email": USER[0], "password": USER[1]})
    assert r.status_code == 401


def test_totp_flow(client: TestClient) -> None:
    headers = login(client, USER)
    secret = client.post("/api/me/totp/setup", headers=headers).json()["secret"]
    assert (
        client.post("/api/me/totp/enable", headers=headers, json={"code": "000000"}).status_code
        == 400
    )
    code = pyotp.TOTP(secret).now()
    assert client.post("/api/me/totp/enable", headers=headers, json={"code": code}).json()[
        "totp_enabled"
    ]

    r = client.post("/api/auth/login", json={"email": USER[0], "password": USER[1]}).json()
    assert r["mfa_required"] and r["access_token"] is None
    bad = client.post("/api/auth/login/mfa", json={"mfa_token": r["mfa_token"], "code": "123456"})
    assert bad.status_code == 401
    ok = client.post(
        "/api/auth/login/mfa", json={"mfa_token": r["mfa_token"], "code": pyotp.TOTP(secret).now()}
    )
    assert ok.status_code == 200 and ok.json()["access_token"]
    assert (
        client.get("/api/me", headers={"Authorization": f"Bearer {r['mfa_token']}"}).status_code
        == 401
    )


def test_password_reset(client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level("INFO")
    assert (
        client.post(
            "/api/auth/password-reset/request", json={"email": "nobody@example.org"}
        ).status_code
        == 202
    )
    assert (
        client.post("/api/auth/password-reset/request", json={"email": USER[0]}).status_code == 202
    )
    match = re.search(r"token=([\w-]+)", caplog.text)
    assert match
    token = match.group(1)
    old_headers = login(client, USER)
    r = client.post(
        "/api/auth/password-reset/confirm",
        json={"token": token, "new_password": "brand-new-password"},
    )
    assert r.status_code == 204
    assert client.get("/api/me", headers=old_headers).status_code == 401
    assert (
        client.post(
            "/api/auth/password-reset/confirm",
            json={"token": token, "new_password": "another-password"},
        ).status_code
        == 400
    )
    login(client, (USER[0], "brand-new-password"))


def test_last_admin_protected(client: TestClient) -> None:
    headers = login(client, ADMIN)
    me = client.get("/api/me", headers=headers).json()
    r = client.patch(f"/api/users/{me['id']}", headers=headers, json={"role": "user"})
    assert r.status_code == 409


def test_deactivated_user_loses_access(client: TestClient) -> None:
    admin = login(client, ADMIN)
    user = login(client, USER)
    uid = client.get("/api/me", headers=user).json()["id"]
    client.patch(f"/api/users/{uid}", headers=admin, json={"is_active": False})
    assert client.get("/api/me", headers=user).status_code == 401


def test_password_reset_is_throttled(client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level("INFO")
    for _ in range(3):
        assert (
            client.post("/api/auth/password-reset/request", json={"email": USER[0]}).status_code
            == 202
        )
    assert len(re.findall(r"token=([\w-]+)", caplog.text)) == 1


def test_admin_triggered_reset(client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level("INFO")
    admin = login(client, ADMIN)
    uid = login_user_id(client)
    assert client.post(f"/api/users/{uid}/send-password-reset", headers=admin).status_code == 202
    assert "token=" in caplog.text


def login_user_id(client: TestClient) -> int:
    headers = login(client, USER)
    return int(client.get("/api/me", headers=headers).json()["id"])
