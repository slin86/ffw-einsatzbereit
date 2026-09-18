import logging
import random
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from einsatzbereit.config import get_settings
from einsatzbereit.models import (
    AppState,
    Certification,
    CertificationKind,
    Completion,
    Member,
    Position,
    User,
    UserRole,
    ValidityMode,
)
from einsatzbereit.security import hash_password, now_utc

log = logging.getLogger(__name__)

CERTS = [
    (
        "Belastungsübung Atemschutz",
        "AGT-Ü",
        CertificationKind.EXERCISE,
        ValidityMode.FIXED_DURATION,
        12,
        60,
    ),
    (
        "Unterweisung Atemschutz",
        "AGT-U",
        CertificationKind.SEMINAR,
        ValidityMode.END_OF_YEAR,
        12,
        60,
    ),
    ("G26.3 Untersuchung", "G26", CertificationKind.TEST, ValidityMode.MANUAL, None, 90),
    ("Erste Hilfe", "EH", CertificationKind.TRAINING, ValidityMode.FIXED_DURATION, 24, 60),
    ("UVV-Unterweisung", "UVV", CertificationKind.SEMINAR, ValidityMode.END_OF_YEAR, 12, 45),
    ("Sprechfunk", "FuK", CertificationKind.TRAINING, ValidityMode.UNLIMITED, None, 0),
    (
        "Maschinisten-Fortbildung",
        "MA",
        CertificationKind.TRAINING,
        ValidityMode.FIXED_DURATION,
        12,
        60,
    ),
    (
        "Fahrsicherheitstraining",
        "FST",
        CertificationKind.EXERCISE,
        ValidityMode.FIXED_DURATION,
        36,
        90,
    ),
    ("Truppführer-Lehrgang", "TF", CertificationKind.TRAINING, ValidityMode.UNLIMITED, None, 0),
    ("Absturzsicherung", "AbS", CertificationKind.EXERCISE, ValidityMode.FIXED_DURATION, 12, 60),
]

POSITIONS = {
    "Grundausbildung": ["EH", "UVV", "FuK"],
    "Atemschutzgeräteträger": ["AGT-Ü", "AGT-U", "G26"],
    "Maschinist": ["MA", "FST"],
    "Truppführer": ["TF"],
    "Absturzsicherung": ["AbS"],
}

FIRST = [
    "Anna",
    "Ben",
    "Clara",
    "David",
    "Eva",
    "Finn",
    "Greta",
    "Hannes",
    "Ida",
    "Jonas",
    "Klara",
    "Lars",
    "Mia",
    "Nils",
    "Ole",
    "Paula",
    "Quirin",
    "Rieke",
    "Sven",
    "Tina",
]
LAST = [
    "Albers",
    "Brandt",
    "Claußen",
    "Dreyer",
    "Ehlers",
    "Fock",
    "Gerdes",
    "Hansen",
    "Jacobs",
    "Kröger",
    "Lüdemann",
    "Meyer",
    "Nagel",
    "Ohlsen",
    "Petersen",
    "Rathje",
    "Schütt",
    "Thode",
    "Voß",
    "Wendt",
    "Harms",
    "Jensen",
    "Köhler",
    "Lange",
    "Möller",
]


def _lock_state(db: Session) -> AppState:
    """
    Loads the single application state row with a row lock, so concurrent starts wait for each
    other. The row is created if the migration did not add it, which happens in tests.
    """
    state = db.scalar(select(AppState).where(AppState.id == 1).with_for_update())
    if state is None:
        state = AppState(id=1, initialized=False)
        db.add(state)
        db.flush()
    return state


def seed_catalog(db: Session) -> dict[str, Position]:
    """
    Adds the standard certifications and the positions that require them. Returns the positions
    by name.
    """
    certs = {
        short: Certification(
            name=name,
            short_name=short,
            kind=kind,
            validity_mode=mode,
            validity_months=months,
            warn_days=warn,
            sort_order=i,
        )
        for i, (name, short, kind, mode, months, warn) in enumerate(CERTS)
    }
    db.add_all(certs.values())
    positions = {
        name: Position(name=name, certifications=[certs[s] for s in shorts])
        for name, shorts in POSITIONS.items()
    }
    db.add_all(positions.values())
    return positions


def seed_demo_members(db: Session, positions: dict[str, Position], recorded_by: User) -> None:
    """
    Adds 50 demo members with random positions and completions. The random generator uses a
    fixed seed, so the data is reproducible. About one in twelve required certifications is left
    missing and about one in ten is old enough to be expired or expiring.
    """
    rnd = random.Random(112)  # noqa: S311
    today = date.today()
    for n in range(50):
        pos = [positions["Grundausbildung"]]
        for extra, probability in (
            ("Atemschutzgeräteträger", 0.6),
            ("Maschinist", 0.3),
            ("Truppführer", 0.35),
            ("Absturzsicherung", 0.15),
        ):
            if rnd.random() < probability:
                pos.append(positions[extra])
        member = Member(
            number=str(101 + n),
            first_name=rnd.choice(FIRST),
            last_name=rnd.choice(LAST),
            positions=pos,
        )
        db.add(member)
        for cert in sorted({c for p in pos for c in p.certifications}, key=lambda c: c.sort_order):
            roll = rnd.random()
            if roll < 0.08:
                continue
            age = rnd.randint(0, 420) if roll < 0.9 else rnd.randint(330, 800)
            done = today - timedelta(days=age)
            manual = (
                done + timedelta(days=rnd.choice([365, 1095]))
                if cert.validity_mode == ValidityMode.MANUAL
                else None
            )
            member.completions.append(
                Completion(
                    certification=cert,
                    completed_on=done,
                    manual_expires_on=manual,
                    recorded_by=recorded_by,
                )
            )


def run_initial_seed(db: Session) -> bool:
    """
    Seeds the database exactly once, controlled by the initialized flag in the application
    state. The first start creates the admin from the environment and the standard catalog, and
    with demo data enabled also the demo members. The flag is set in the same transaction, so
    later starts never seed again, even if the admin or the catalog were deleted. Without admin
    credentials nothing is seeded and the flag stays unset, otherwise nobody could ever log in.
    Returns whether the seed ran.
    """
    s = get_settings()
    state = _lock_state(db)
    if state.initialized:
        db.rollback()
        return False
    if not (s.initial_admin_email and s.initial_admin_password):
        db.rollback()
        log.warning(
            "First start without EB_INITIAL_ADMIN_EMAIL and EB_INITIAL_ADMIN_PASSWORD, seed skipped"
        )
        return False
    admin = User(
        username=s.initial_admin_username.lower(),
        email=s.initial_admin_email.lower(),
        display_name="Administrator",
        password_hash=hash_password(s.initial_admin_password),
        role=UserRole.ADMIN,
    )
    db.add(admin)
    positions = seed_catalog(db)
    if s.seed_demo_data:
        seed_demo_members(db, positions, admin)
    state.initialized = True
    state.initialized_at = now_utc()
    db.commit()
    log.info("Initial seed done, admin %s created, demo data %s", admin.email, s.seed_demo_data)
    return True
