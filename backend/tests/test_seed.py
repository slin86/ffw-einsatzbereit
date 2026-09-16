from collections.abc import Iterator
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, sessionmaker

from einsatzbereit import seed
from einsatzbereit.config import Settings
from einsatzbereit.main import create_app
from einsatzbereit.models import (
    AppState,
    Certification,
    Completion,
    Member,
    Position,
    User,
    UserRole,
    member_positions,
    position_certifications,
)


@pytest.fixture
def settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[dict[str, object]]:
    values: dict[str, object] = {
        "initial_admin_email": "Chief@Example.org",
        "initial_admin_password": "chief-password-1",
        "seed_demo_data": False,
    }
    monkeypatch.setattr(seed, "get_settings", lambda: Settings(**values))  # type: ignore[arg-type]
    yield values


def count(db: Session, model: type) -> int:
    return db.scalar(select(func.count()).select_from(model)) or 0


def state(db: Session) -> AppState | None:
    db.expire_all()
    return db.get(AppState, 1)


def test_first_start_seeds_admin_and_catalog(db: Session, settings: dict[str, object]) -> None:
    assert seed.run_initial_seed(db) is True
    admin = db.scalars(select(User)).one()
    assert (admin.email, admin.role) == ("chief@example.org", UserRole.ADMIN)
    assert count(db, Certification) == len(seed.CERTS)
    assert {p.name for p in db.scalars(select(Position))} == set(seed.POSITIONS)
    assert count(db, Member) == 0
    row = state(db)
    assert row is not None and row.initialized is True
    assert row.initialized_at is not None


def test_seed_runs_only_once(db: Session, settings: dict[str, object]) -> None:
    assert seed.run_initial_seed(db) is True
    assert seed.run_initial_seed(db) is False
    assert count(db, User) == 1
    assert count(db, Certification) == len(seed.CERTS)


def test_no_reseed_after_admin_and_catalog_were_deleted(
    db: Session, settings: dict[str, object]
) -> None:
    seed.run_initial_seed(db)
    db.execute(delete(Position))
    db.execute(delete(Certification))
    db.execute(delete(User))
    db.commit()
    assert seed.run_initial_seed(db) is False
    assert count(db, User) == 0
    assert count(db, Certification) == 0


def test_missing_credentials_postpone_the_seed(
    db: Session, settings: dict[str, object], caplog: pytest.LogCaptureFixture
) -> None:
    settings["initial_admin_password"] = ""
    assert seed.run_initial_seed(db) is False
    assert "seed skipped" in caplog.text
    assert count(db, User) == 0
    assert count(db, Certification) == 0
    row = state(db)
    assert row is None or row.initialized is False

    settings["initial_admin_password"] = "chief-password-1"
    assert seed.run_initial_seed(db) is True
    row = state(db)
    assert row is not None and row.initialized is True


def test_demo_data(db: Session, settings: dict[str, object]) -> None:
    settings["seed_demo_data"] = True
    assert seed.run_initial_seed(db) is True
    assert count(db, Member) == 50
    completions = db.scalars(select(Completion)).all()
    admin = db.scalars(select(User)).one()
    assert completions
    assert all(c.recorded_by_id == admin.id for c in completions)
    assert all(c.completed_on <= date.today() for c in completions)
    manual = [c for c in completions if c.certification.short_name == "G26"]
    assert manual and all(c.manual_expires_on is not None for c in manual)


def test_demo_data_is_reproducible(
    session_factory: sessionmaker[Session], settings: dict[str, object]
) -> None:
    settings["seed_demo_data"] = True
    snapshots = []
    for _ in range(2):
        with session_factory() as db:
            db.execute(delete(Completion))
            db.execute(member_positions.delete())
            db.execute(position_certifications.delete())
            db.execute(delete(Member))
            db.execute(delete(Position))
            db.execute(delete(Certification))
            db.execute(delete(User))
            db.execute(delete(AppState))
            db.commit()
            seed.run_initial_seed(db)
            members = db.scalars(select(Member).order_by(Member.number)).all()
            snapshots.append(
                [(m.number, m.last_name, len(m.positions), len(m.completions)) for m in members]
            )
    assert snapshots[0] == snapshots[1]


def test_application_start_seeds_once(
    session_factory: sessionmaker[Session], settings: dict[str, object]
) -> None:
    for _ in range(2):
        with TestClient(create_app()):
            pass
    with session_factory() as db:
        assert count(db, User) == 1
        row = state(db)
        assert row is not None and row.initialized is True
    login = {"email": "chief@example.org", "password": "chief-password-1"}
    with TestClient(create_app()) as client:
        assert client.post("/api/auth/login", json=login).status_code == 200
