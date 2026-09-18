import os

os.environ["EB_DATABASE_URL"] = "sqlite://"
os.environ["EB_COOKIE_SECURE"] = "false"
os.environ["EB_STATIC_DIR"] = ""
os.environ["EB_INITIAL_ADMIN_EMAIL"] = ""
os.environ["EB_INITIAL_ADMIN_PASSWORD"] = ""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from einsatzbereit import db as db_module
from einsatzbereit.db import Base, get_db
from einsatzbereit.main import create_app
from einsatzbereit.models import AppState, User, UserRole
from einsatzbereit.security import hash_password

ADMIN = ("admin@example.org", "admin-password-123")
USER = ("user@example.org", "user-password-123")


TEST_DATABASE_URL = os.environ.get("EB_TEST_DATABASE_URL", "")


def _make_engine() -> Engine:
    if TEST_DATABASE_URL:
        return create_engine(TEST_DATABASE_URL)
    return create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )


@pytest.fixture
def session_factory(monkeypatch: pytest.MonkeyPatch) -> Iterator[sessionmaker[Session]]:
    engine = _make_engine()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(db_module, "get_sessionmaker", lambda: factory)
    import einsatzbereit.main as main_module

    monkeypatch.setattr(main_module, "get_sessionmaker", lambda: factory)
    yield factory
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    with session_factory() as s:
        yield s


@pytest.fixture
def client(session_factory: sessionmaker[Session]) -> Iterator[TestClient]:
    app = create_app()

    def _get_db() -> Iterator[Session]:
        with session_factory() as s:
            yield s

    app.dependency_overrides[get_db] = _get_db
    with session_factory() as s:
        s.add_all(
            [
                AppState(id=1, initialized=True),
                User(
                    username="admin",
                    email=ADMIN[0],
                    display_name="Administrator",
                    role=UserRole.ADMIN,
                    password_hash=hash_password(ADMIN[1]),
                ),
                User(
                    username="anwender",
                    email=USER[0],
                    display_name="Anwender",
                    role=UserRole.USER,
                    password_hash=hash_password(USER[1]),
                ),
            ]
        )
        s.commit()
    with TestClient(app) as c:
        yield c


def login(client: TestClient, creds: tuple[str, str]) -> dict[str, str]:
    r = client.post("/api/auth/login", json={"login": creds[0], "password": creds[1]})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def admin_headers(client: TestClient) -> dict[str, str]:
    return login(client, ADMIN)


@pytest.fixture
def user_headers(client: TestClient) -> dict[str, str]:
    return login(client, USER)
