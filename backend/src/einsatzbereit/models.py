"""ORM models.

Domain vocabulary (German UI term -> code name):
    Kamerad    -> Member
    Funktion   -> Position        (e.g. AGT, Maschinist)
    Nachweis   -> Certification   (seminar, exercise, test, further training)
    Abschluss  -> Completion
    Benutzer   -> User            (people who log in; members never log in)
"""

import enum
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from einsatzbereit.db import Base


class UserRole(enum.StrEnum):
    ADMIN = "admin"
    USER = "user"


class CertificationKind(enum.StrEnum):
    SEMINAR = "seminar"
    EXERCISE = "exercise"
    TEST = "test"
    TRAINING = "training"


class ValidityMode(enum.StrEnum):
    UNLIMITED = "unlimited"
    """Never expires."""
    FIXED_DURATION = "fixed_duration"
    """Expires ``validity_months`` after the completion date."""
    END_OF_YEAR = "end_of_year"
    """Expires on Dec 31 of the year reached after ``validity_months``."""
    MANUAL = "manual"
    """Expiry date is entered per completion."""


def _enum(e: type[enum.StrEnum]) -> Enum:
    return Enum(e, native_enum=False, length=32, values_callable=lambda x: [m.value for m in x])


member_positions = Table(
    "member_positions",
    Base.metadata,
    Column("member_id", ForeignKey("members.id", ondelete="CASCADE"), primary_key=True),
    Column("position_id", ForeignKey("positions.id", ondelete="CASCADE"), primary_key=True),
)

position_certifications = Table(
    "position_certifications",
    Base.metadata,
    Column("position_id", ForeignKey("positions.id", ondelete="CASCADE"), primary_key=True),
    Column(
        "certification_id", ForeignKey("certifications.id", ondelete="CASCADE"), primary_key=True
    ),
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(_enum(UserRole), default=UserRole.USER)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    totp_secret: Mapped[str | None] = mapped_column(String(64), nullable=True)
    totp_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    failed_logins: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    token_version: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    family_id: Mapped[str] = mapped_column(String(36), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Position(Base):
    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    description: Mapped[str] = mapped_column(Text, default="")

    certifications: Mapped[list["Certification"]] = relationship(
        secondary=position_certifications, order_by="Certification.name"
    )


class Certification(Base):
    __tablename__ = "certifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    short_name: Mapped[str] = mapped_column(String(12), default="")
    """Abbreviation used as column header in the compact status board."""
    kind: Mapped[CertificationKind] = mapped_column(_enum(CertificationKind))
    description: Mapped[str] = mapped_column(Text, default="")
    validity_mode: Mapped[ValidityMode] = mapped_column(_enum(ValidityMode))
    validity_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    warn_days: Mapped[int] = mapped_column(Integer, default=60)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Member(Base):
    __tablename__ = "members"

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    last_name: Mapped[str] = mapped_column(String(80))
    first_name: Mapped[str] = mapped_column(String(80))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    positions: Mapped[list[Position]] = relationship(
        secondary=member_positions, order_by="Position.name"
    )
    completions: Mapped[list["Completion"]] = relationship(
        back_populates="member", cascade="all, delete-orphan"
    )


class Completion(Base):
    __tablename__ = "completions"

    id: Mapped[int] = mapped_column(primary_key=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id", ondelete="CASCADE"), index=True)
    certification_id: Mapped[int] = mapped_column(
        ForeignKey("certifications.id", ondelete="RESTRICT"), index=True
    )
    completed_on: Mapped[date] = mapped_column(Date)
    manual_expires_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    note: Mapped[str] = mapped_column(Text, default="")
    recorded_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    member: Mapped[Member] = relationship(back_populates="completions")
    certification: Mapped[Certification] = relationship()
    recorded_by: Mapped[User | None] = relationship()
