import smtplib
from collections.abc import Iterator
from pathlib import Path
from typing import Any, ClassVar

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from einsatzbereit import mailer
from einsatzbereit.config import DEV_JWT_SECRET, Settings, get_settings
from einsatzbereit.db import get_db, get_engine, get_sessionmaker
from einsatzbereit.main import create_app


def test_health_and_security_headers(client: TestClient) -> None:
    r = client.get("/healthz")
    assert r.json() == {"status": "ok"}
    assert "frame-ancestors 'none'" in r.headers["content-security-policy"]
    assert r.headers["x-content-type-options"] == "nosniff"
    assert client.get("/readyz").json() == {"status": "ok"}
    api = client.get("/api/overview")
    assert api.headers["cache-control"] == "no-store"


def test_production_safety() -> None:
    Settings(cookie_secure=False).check_production_safety()
    Settings(cookie_secure=True, jwt_secret="x" * 40).check_production_safety()
    with pytest.raises(RuntimeError, match="EB_JWT_SECRET"):
        Settings(cookie_secure=True, jwt_secret=DEV_JWT_SECRET).check_production_safety()


def test_app_refuses_to_start_with_dev_secret(
    monkeypatch: pytest.MonkeyPatch, session_factory: sessionmaker[Session]
) -> None:
    monkeypatch.setenv("EB_COOKIE_SECURE", "true")
    get_settings.cache_clear()
    try:
        with pytest.raises(RuntimeError), TestClient(create_app()):
            pass
    finally:
        get_settings.cache_clear()


@pytest.fixture
def spa_client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, session_factory: sessionmaker[Session]
) -> Iterator[TestClient]:
    static = tmp_path / "static"
    (static / "assets").mkdir(parents=True)
    (static / "index.html").write_text("<html>app</html>")
    (static / "icon.svg").write_text("<svg/>")
    (static / "assets" / "app.js").write_text("console.log(1)")
    (tmp_path / "secret.txt").write_text("secret")
    monkeypatch.setenv("EB_STATIC_DIR", str(static))
    get_settings.cache_clear()
    try:
        with TestClient(create_app()) as c:
            yield c
    finally:
        get_settings.cache_clear()


def test_spa_serving(spa_client: TestClient) -> None:
    assert spa_client.get("/").text == "<html>app</html>"
    deep = spa_client.get("/kameraden/12")
    assert deep.text == "<html>app</html>"
    assert deep.headers["cache-control"] == "no-cache"
    assert spa_client.get("/icon.svg").text == "<svg/>"
    assert spa_client.get("/assets/app.js").text == "console.log(1)"
    assert spa_client.get("/api/does-not-exist").status_code == 404


def test_spa_blocks_path_traversal(spa_client: TestClient) -> None:
    for path in ("/..%2fsecret.txt", "/%2e%2e/secret.txt"):
        assert spa_client.get(path).text == "<html>app</html>"
    assert spa_client.get("/assets/..%2f..%2fsecret.txt").status_code == 404


def test_spa_without_assets_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "index.html").write_text("<html>app</html>")
    monkeypatch.setenv("EB_STATIC_DIR", str(tmp_path))
    get_settings.cache_clear()
    try:
        app = create_app()
    finally:
        get_settings.cache_clear()
    assert not any(getattr(r, "name", "") == "assets" for r in app.routes)
    assert any(getattr(r, "path", "") == "/{path:path}" for r in app.routes)


def test_no_spa_without_build(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EB_STATIC_DIR", str(tmp_path))
    get_settings.cache_clear()
    try:
        app = create_app()
    finally:
        get_settings.cache_clear()
    assert not any(getattr(r, "path", "") == "/{path:path}" for r in app.routes)


def test_db_helpers() -> None:
    assert get_engine().url.drivername == "sqlite"
    gen = get_db()
    session = next(gen)
    assert isinstance(session, Session)
    assert get_sessionmaker().kw["bind"] is get_engine()
    assert list(gen) == []


class FakeSMTP:
    sent: ClassVar[list[Any]] = []
    fail: ClassVar[bool] = False

    def __init__(self, host: str, port: int, timeout: int) -> None:
        self.calls: list[str] = [f"connect {host}:{port}"]

    def __enter__(self) -> "FakeSMTP":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def starttls(self) -> None:
        self.calls.append("starttls")

    def login(self, user: str, password: str) -> None:
        self.calls.append(f"login {user}")

    def send_message(self, msg: Any) -> None:
        if FakeSMTP.fail:
            raise smtplib.SMTPException("boom")
        FakeSMTP.sent.append((self.calls, msg))


def test_mailer_smtp(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    settings = Settings(
        smtp_host="smtp.test", smtp_port=2525, smtp_username="relay", smtp_password="pw"
    )
    monkeypatch.setattr(mailer, "get_settings", lambda: settings)
    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    FakeSMTP.sent.clear()
    mailer.send_mail("a@example.org", "Betreff", "Hallo")
    calls, msg = FakeSMTP.sent[0]
    assert calls == ["connect smtp.test:2525", "starttls", "login relay"]
    assert msg["To"] == "a@example.org" and msg["Subject"] == "Betreff"

    FakeSMTP.fail = True
    try:
        mailer.send_mail("a@example.org", "Betreff", "Hallo")
    finally:
        FakeSMTP.fail = False
    assert "Failed to send mail" in caplog.text


def test_mailer_plain_smtp_without_login(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(smtp_host="smtp.test", smtp_starttls=False)
    monkeypatch.setattr(mailer, "get_settings", lambda: settings)
    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    FakeSMTP.sent.clear()
    mailer.send_mail("a@example.org", "x", "y")
    assert FakeSMTP.sent[0][0] == ["connect smtp.test:587"]
