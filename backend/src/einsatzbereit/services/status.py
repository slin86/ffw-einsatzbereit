"""Expiry calculation and status matrix.

This module holds the core business rules and is deliberately free of HTTP concerns.
"""

import calendar
import enum
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from einsatzbereit.models import Certification, Completion, Member, Position, ValidityMode


class CellStatus(enum.StrEnum):
    """Status of one member/certification pair."""

    MISSING = "missing"
    EXPIRED = "expired"
    EXPIRING = "expiring"
    VALID = "valid"
    NOT_REQUIRED = "not_required"


SEVERITY: dict[CellStatus, int] = {
    CellStatus.MISSING: 0,
    CellStatus.EXPIRED: 1,
    CellStatus.EXPIRING: 2,
    CellStatus.VALID: 3,
    CellStatus.NOT_REQUIRED: 4,
}

OPEN_STATUSES = frozenset({CellStatus.MISSING, CellStatus.EXPIRED, CellStatus.EXPIRING})


def add_months(d: date, months: int) -> date:
    month_index = d.month - 1 + months
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def expiry_date(cert: Certification, completion: Completion) -> date | None:
    """Return the last day on which the completion is valid, or ``None`` if unlimited.

    Expiry is computed on read (not stored) so that changing a certification's
    validity rules immediately applies to all existing completions.
    """
    match cert.validity_mode:
        case ValidityMode.UNLIMITED:
            return None
        case ValidityMode.MANUAL:
            return completion.manual_expires_on
        case ValidityMode.FIXED_DURATION:
            if cert.validity_months is None:
                return None
            return add_months(completion.completed_on, cert.validity_months) - timedelta(days=1)
        case ValidityMode.END_OF_YEAR:
            if cert.validity_months is None:
                return None
            reached = add_months(completion.completed_on, cert.validity_months)
            return date(reached.year, 12, 31)


def evaluate(
    cert: Certification, latest: Completion | None, required: bool, today: date
) -> tuple[CellStatus, date | None]:
    if latest is None:
        return (CellStatus.MISSING if required else CellStatus.NOT_REQUIRED), None
    expires = expiry_date(cert, latest)
    if expires is None:
        status = CellStatus.VALID
    elif expires < today:
        status = CellStatus.EXPIRED
    elif (expires - today).days <= cert.warn_days:
        status = CellStatus.EXPIRING
    else:
        status = CellStatus.VALID
    if not required and status != CellStatus.VALID:
        # Certifications not required by any of the member's positions never create TODOs.
        status = CellStatus.NOT_REQUIRED
    return status, expires


def required_certification_ids(member: Member) -> set[int]:
    return {c.id for p in member.positions for c in p.certifications if c.is_active}


def latest_completions(completions: Iterable[Completion]) -> dict[int, Completion]:
    latest: dict[int, Completion] = {}
    for c in completions:
        cur = latest.get(c.certification_id)
        if cur is None or (c.completed_on, c.id) > (cur.completed_on, cur.id):
            latest[c.certification_id] = c
    return latest


@dataclass(frozen=True)
class Cell:
    certification_id: int
    required: bool
    status: CellStatus
    completed_on: date | None
    expires_on: date | None


@dataclass
class MatrixRow:
    member: Member
    cells: list[Cell]

    @property
    def worst_status(self) -> CellStatus:
        relevant = [c.status for c in self.cells] or [CellStatus.NOT_REQUIRED]
        return min(relevant, key=SEVERITY.__getitem__)

    @property
    def open_count(self) -> int:
        return sum(1 for c in self.cells if c.status in OPEN_STATUSES)


@dataclass
class MatrixFilter:
    statuses: set[CellStatus] = field(default_factory=set)
    position_id: int | None = None
    certification_id: int | None = None
    query: str = ""
    include_inactive: bool = False
    only_open: bool = False


@dataclass
class Matrix:
    today: date
    certifications: list[Certification]
    rows: list[MatrixRow]

    def counts(self) -> dict[CellStatus, int]:
        result = dict.fromkeys(CellStatus, 0)
        for row in self.rows:
            for cell in row.cells:
                result[cell.status] += 1
        return result


def build_cells(member: Member, certs: Sequence[Certification], today: date) -> list[Cell]:
    required = required_certification_ids(member)
    latest = latest_completions(member.completions)
    cells = []
    for cert in certs:
        comp = latest.get(cert.id)
        status, expires = evaluate(cert, comp, cert.id in required, today)
        cells.append(
            Cell(
                certification_id=cert.id,
                required=cert.id in required,
                status=status,
                completed_on=comp.completed_on if comp else None,
                expires_on=expires,
            )
        )
    return cells


def active_certifications(db: Session) -> list[Certification]:
    stmt = (
        select(Certification)
        .where(Certification.is_active.is_(True))
        .order_by(Certification.sort_order, Certification.name)
    )
    return list(db.scalars(stmt))


def build_matrix(db: Session, flt: MatrixFilter, today: date | None = None) -> Matrix:
    today = today or date.today()
    certs = active_certifications(db)
    if flt.certification_id is not None:
        certs = [c for c in certs if c.id == flt.certification_id]

    stmt = (
        select(Member)
        .options(
            selectinload(Member.positions).selectinload(Position.certifications),
            selectinload(Member.completions),
        )
        .order_by(Member.last_name, Member.first_name)
    )
    if not flt.include_inactive:
        stmt = stmt.where(Member.is_active.is_(True))
    if flt.position_id is not None:
        stmt = stmt.where(Member.positions.any(Position.id == flt.position_id))
    if flt.query.strip():
        like = f"%{flt.query.strip()}%"
        stmt = stmt.where(
            Member.last_name.ilike(like) | Member.first_name.ilike(like) | Member.number.ilike(like)
        )

    rows: list[MatrixRow] = []
    for member in db.scalars(stmt):
        row = MatrixRow(member=member, cells=build_cells(member, certs, today))
        if flt.statuses and not any(c.status in flt.statuses for c in row.cells):
            continue
        if flt.only_open and row.open_count == 0:
            continue
        rows.append(row)

    if flt.only_open:
        rows.sort(key=lambda r: (SEVERITY[r.worst_status], -r.open_count, r.member.last_name))
    return Matrix(today=today, certifications=certs, rows=rows)
