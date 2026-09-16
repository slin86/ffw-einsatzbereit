"""Fill an empty database with demo data for local development.

Usage: ``uv run python -m einsatzbereit.seed``
"""

import random
from datetime import date, timedelta

from sqlalchemy import func, select

from einsatzbereit.db import Base, get_engine, get_sessionmaker
from einsatzbereit.models import (
    Certification,
    CertificationKind,
    Completion,
    Member,
    Position,
    User,
    UserRole,
    ValidityMode,
)
from einsatzbereit.security import hash_password

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


def main() -> None:
    Base.metadata.create_all(get_engine())
    rnd = random.Random(112)  # noqa: S311
    today = date.today()
    with get_sessionmaker()() as db:
        if db.scalar(select(func.count()).select_from(Member)):
            print("Database already contains members – nothing to do.")
            return
        admin = db.scalar(select(User).where(User.role == UserRole.ADMIN).limit(1))
        if admin is None:
            admin = User(
                email="admin@example.org",
                display_name="Admin",
                role=UserRole.ADMIN,
                password_hash=hash_password("admin-password"),
            )
            db.add(admin)
        certs = {}
        for i, (name, short, kind, mode, months, warn) in enumerate(CERTS):
            certs[short] = Certification(
                name=name,
                short_name=short,
                kind=kind,
                validity_mode=mode,
                validity_months=months,
                warn_days=warn,
                sort_order=i,
            )
        db.add_all(certs.values())
        positions = {
            name: Position(name=name, certifications=[certs[s] for s in shorts])
            for name, shorts in POSITIONS.items()
        }
        db.add_all(positions.values())

        for n in range(50):
            pos = [positions["Grundausbildung"]]
            for extra, p in (
                ("Atemschutzgeräteträger", 0.6),
                ("Maschinist", 0.3),
                ("Truppführer", 0.35),
                ("Absturzsicherung", 0.15),
            ):
                if rnd.random() < p:
                    pos.append(positions[extra])
            member = Member(
                number=str(101 + n),
                first_name=rnd.choice(FIRST),
                last_name=rnd.choice(LAST),
                positions=pos,
            )
            db.add(member)
            for cert in {c for p in pos for c in p.certifications}:
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
                        recorded_by=admin,
                    )
                )
        db.commit()
    print("Demo data created. Login: admin@example.org / admin-password")


if __name__ == "__main__":
    main()
