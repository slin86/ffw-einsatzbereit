"""Read access to the change log."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import Select, select

from einsatzbereit.deps import AdminUser, CurrentUser, DbSession
from einsatzbereit.models import AuditEntry, Member
from einsatzbereit.schemas import AuditEntryOut, AuditPage
from einsatzbereit.services.audit import EntityType

router = APIRouter(prefix="/api", tags=["audit"])

Limit = Annotated[int, Query(ge=1, le=200)]


def _page(
    db: DbSession, stmt: Select[tuple[AuditEntry]], limit: int, before_id: int | None
) -> AuditPage:
    if before_id is not None:
        stmt = stmt.where(AuditEntry.id < before_id)
    rows = list(db.scalars(stmt.order_by(AuditEntry.id.desc()).limit(limit + 1)))
    has_more = len(rows) > limit
    rows = rows[:limit]
    return AuditPage(
        entries=[AuditEntryOut.model_validate(r) for r in rows],
        next_before_id=rows[-1].id if has_more else None,
    )


@router.get("/audit", response_model=AuditPage)
def list_audit(
    _: AdminUser,
    db: DbSession,
    entity_type: EntityType | None = None,
    q: str = "",
    limit: Limit = 50,
    before_id: int | None = None,
) -> AuditPage:
    """Full change log, newest first. Admins only."""
    stmt = select(AuditEntry)
    if entity_type is not None:
        stmt = stmt.where(AuditEntry.entity_type == entity_type.value)
    if q.strip():
        like = f"%{q.strip()}%"
        stmt = stmt.where(AuditEntry.entity_label.ilike(like) | AuditEntry.user_name.ilike(like))
    return _page(db, stmt, limit, before_id)


@router.get("/members/{member_id}/audit", response_model=AuditPage)
def member_audit(
    member_id: int,
    _: CurrentUser,
    db: DbSession,
    limit: Limit = 20,
    before_id: int | None = None,
) -> AuditPage:
    """Changes to one member and their completions. Visible to all users."""
    if db.get(Member, member_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Member not found")
    stmt = select(AuditEntry).where(AuditEntry.member_id == member_id)
    return _page(db, stmt, limit, before_id)
