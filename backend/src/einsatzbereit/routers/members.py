from datetime import date

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from einsatzbereit.deps import AdminUser, CurrentUser, DbSession
from einsatzbereit.models import (
    AuditEntry,
    Certification,
    Completion,
    Member,
    Position,
    User,
    UserRole,
    ValidityMode,
)
from einsatzbereit.schemas import (
    BulkCompletionIn,
    BulkCompletionOut,
    CellOut,
    CompletionIn,
    CompletionOut,
    DeletedOut,
    MemberDetailOut,
    MemberIdsIn,
    MemberIn,
    MemberOut,
)
from einsatzbereit.services import audit
from einsatzbereit.services.audit import Action, EntityType
from einsatzbereit.services.status import active_certifications, build_cells, expiry_date

router = APIRouter(prefix="/api", tags=["members"])


def _get_member(db: DbSession, member_id: int) -> Member:
    member = db.get(Member, member_id)
    if member is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Member not found")
    return member


def _load_positions(db: DbSession, ids: list[int]) -> list[Position]:
    positions = list(db.scalars(select(Position).where(Position.id.in_(ids))))
    if len(positions) != len(set(ids)):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Unknown position id")
    return positions


def _flush(db: DbSession) -> None:
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Number already in use") from exc


def completion_out(c: Completion) -> CompletionOut:
    return CompletionOut(
        id=c.id,
        member_id=c.member_id,
        certification_id=c.certification_id,
        certification_name=c.certification.name,
        completed_on=c.completed_on,
        expires_on=expiry_date(c.certification, c),
        note=c.note,
        recorded_by=c.recorded_by.display_name if c.recorded_by else None,
        recorded_by_id=c.recorded_by_id,
        recorded_at=c.recorded_at,
    )


@router.get("/members", response_model=list[MemberOut])
def list_members(_: CurrentUser, db: DbSession, include_inactive: bool = False) -> list[Member]:
    stmt = (
        select(Member)
        .options(selectinload(Member.positions))
        .order_by(Member.last_name, Member.first_name)
    )
    if not include_inactive:
        stmt = stmt.where(Member.is_active.is_(True))
    return list(db.scalars(stmt))


@router.post("/members", response_model=MemberOut, status_code=status.HTTP_201_CREATED)
def create_member(body: MemberIn, user: CurrentUser, db: DbSession) -> Member:
    member = Member(
        number=body.number.strip(),
        last_name=body.last_name.strip(),
        first_name=body.first_name.strip(),
        is_active=body.is_active,
        positions=_load_positions(db, body.position_ids),
    )
    db.add(member)
    _flush(db)
    audit.record(
        db,
        user,
        EntityType.MEMBER,
        member.id,
        audit.member_label(member),
        Action.CREATE,
        after=audit.member_snapshot(member),
        member_id=member.id,
    )
    db.commit()
    return member


@router.put("/members/{member_id}", response_model=MemberOut)
def update_member(member_id: int, body: MemberIn, user: CurrentUser, db: DbSession) -> Member:
    """
    Updates a member and records the change. Positions are loaded before the member changes,
    otherwise autoflush would write a duplicate number early and the request would fail with a
    server error instead of a conflict.
    """
    member = _get_member(db, member_id)
    positions = _load_positions(db, body.position_ids)
    before = audit.member_snapshot(member)
    member.number = body.number.strip()
    member.last_name = body.last_name.strip()
    member.first_name = body.first_name.strip()
    member.is_active = body.is_active
    member.positions = positions
    _flush(db)
    audit.record(
        db,
        user,
        EntityType.MEMBER,
        member.id,
        audit.member_label(member),
        Action.UPDATE,
        before=before,
        after=audit.member_snapshot(member),
        member_id=member.id,
    )
    db.commit()
    return member


def _delete_members(db: DbSession, admin: User, members: list[Member]) -> int:
    """
    Deletes members with all their completions and their entries in the change log, and writes
    one final log entry per member. The final entry has no member reference, so it survives and
    keeps the deletion visible in the log.
    """
    for member in members:
        label = audit.member_label(member)
        snapshot = audit.member_snapshot(member)
        db.execute(delete(AuditEntry).where(AuditEntry.member_id == member.id))
        db.delete(member)
        db.flush()
        audit.record(db, admin, EntityType.MEMBER, member.id, label, Action.DELETE, before=snapshot)
    db.commit()
    return len(members)


@router.delete("/members/{member_id}", response_model=DeletedOut)
def delete_member(member_id: int, admin: AdminUser, db: DbSession) -> DeletedOut:
    """
    Removes a member permanently. Admins only. Deactivating a member keeps the history and is
    the usual way to retire someone.
    """
    return DeletedOut(deleted=_delete_members(db, admin, [_get_member(db, member_id)]))


@router.post("/members/delete", response_model=DeletedOut)
def delete_members(body: MemberIdsIn, admin: AdminUser, db: DbSession) -> DeletedOut:
    """
    Removes several members permanently in one transaction. Admins only. Unknown ids are
    rejected, so a stale list never deletes a wrong subset.
    """
    members = list(db.scalars(select(Member).where(Member.id.in_(body.member_ids))))
    if {m.id for m in members} != set(body.member_ids):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Unknown member id")
    return DeletedOut(deleted=_delete_members(db, admin, members))


@router.get("/members/{member_id}", response_model=MemberDetailOut)
def member_detail(member_id: int, _: CurrentUser, db: DbSession) -> MemberDetailOut:
    """
    Returns a member with the status of every active certification and the full completion
    history, newest first.
    """
    member = _get_member(db, member_id)
    cells = build_cells(member, active_certifications(db), date.today())
    history = sorted(member.completions, key=lambda c: (c.completed_on, c.id), reverse=True)
    return MemberDetailOut(
        member=MemberOut.model_validate(member),
        cells=[CellOut.model_validate(c, from_attributes=True) for c in cells],
        history=[completion_out(c) for c in history],
    )


def _checked_certification(
    db: DbSession, certification_id: int, completed_on: date, manual_expires_on: date | None
) -> tuple[Certification, date | None]:
    """
    Validates completion input for single and bulk entry. The date must not lie in the future,
    and certifications with manual validity need an expiry date. Returns the certification and
    the expiry date to store, which is only kept for manual validity.
    """
    cert = db.get(Certification, certification_id)
    if cert is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Certification not found")
    if cert.validity_mode == ValidityMode.MANUAL and manual_expires_on is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "This certification requires an expiry date"
        )
    if completed_on > date.today():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Date lies in the future")
    return cert, manual_expires_on if cert.validity_mode == ValidityMode.MANUAL else None


@router.post("/completions", response_model=CompletionOut, status_code=status.HTTP_201_CREATED)
def create_completion(body: CompletionIn, user: CurrentUser, db: DbSession) -> CompletionOut:
    member = _get_member(db, body.member_id)
    cert, manual = _checked_certification(
        db, body.certification_id, body.completed_on, body.manual_expires_on
    )
    completion = Completion(
        member_id=body.member_id,
        certification_id=cert.id,
        completed_on=body.completed_on,
        manual_expires_on=manual,
        note=body.note,
        recorded_by_id=user.id,
        certification=cert,
        member=member,
    )
    db.add(completion)
    db.flush()
    _audit_completion(db, user, completion, Action.CREATE)
    db.commit()
    db.refresh(completion)
    return completion_out(completion)


def _audit_completion(db: DbSession, user: User, c: Completion, action: Action) -> None:
    snapshot = audit.completion_snapshot(c)
    audit.record(
        db,
        user,
        EntityType.COMPLETION,
        c.id,
        f"{audit.member_label(c.member)}: {c.certification.name}",
        action,
        before=snapshot if action == Action.DELETE else None,
        after=snapshot if action == Action.CREATE else None,
        member_id=c.member_id,
    )


@router.post(
    "/completions/bulk", response_model=BulkCompletionOut, status_code=status.HTTP_201_CREATED
)
def create_completions_bulk(
    body: BulkCompletionIn, user: CurrentUser, db: DbSession
) -> BulkCompletionOut:
    """
    Records the same completion for several members in one transaction. Members that already have
    this certification on the same date are skipped, so sending the form twice creates no
    duplicates. Returns the number of new completions.
    """
    cert, manual = _checked_certification(
        db, body.certification_id, body.completed_on, body.manual_expires_on
    )
    members = {m.id: m for m in db.scalars(select(Member).where(Member.id.in_(body.member_ids)))}
    if set(members) != set(body.member_ids):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Unknown member id")
    existing = set(
        db.scalars(
            select(Completion.member_id).where(
                Completion.certification_id == cert.id,
                Completion.completed_on == body.completed_on,
                Completion.member_id.in_(body.member_ids),
            )
        )
    )
    new = [
        Completion(
            member=members[member_id],
            certification=cert,
            completed_on=body.completed_on,
            manual_expires_on=manual,
            note=body.note,
            recorded_by_id=user.id,
        )
        for member_id in body.member_ids
        if member_id not in existing
    ]
    db.add_all(new)
    db.flush()
    for completion in new:
        _audit_completion(db, user, completion, Action.CREATE)
    db.commit()
    return BulkCompletionOut(created=len(new))


@router.delete("/completions/{completion_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_completion(completion_id: int, user: CurrentUser, db: DbSession) -> None:
    """
    Deletes a completion. Admins may delete any entry, other users only the entries they recorded
    themselves.
    """
    completion = db.get(Completion, completion_id)
    if completion is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Completion not found")
    if user.role != UserRole.ADMIN and completion.recorded_by_id != user.id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Only the recording user or an admin may delete"
        )
    _audit_completion(db, user, completion, Action.DELETE)
    db.delete(completion)
    db.commit()
