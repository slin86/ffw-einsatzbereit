import enum
from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from einsatzbereit.models import (
    AuditEntry,
    Certification,
    Completion,
    Member,
    Position,
    User,
)

Snapshot = dict[str, Any]


class EntityType(enum.StrEnum):
    MEMBER = "member"
    COMPLETION = "completion"
    CERTIFICATION = "certification"
    POSITION = "position"
    USER = "user"


class Action(enum.StrEnum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


def _json(value: Any) -> Any:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, enum.Enum):
        return value.value
    return value


def member_snapshot(m: Member) -> Snapshot:
    return {
        "number": m.number,
        "last_name": m.last_name,
        "first_name": m.first_name,
        "is_active": m.is_active,
        "positions": sorted(p.name for p in m.positions),
    }


def member_label(m: Member) -> str:
    return f"{m.last_name}, {m.first_name} ({m.number})"


def completion_snapshot(c: Completion) -> Snapshot:
    return {
        "certification": c.certification.name,
        "completed_on": _json(c.completed_on),
        "manual_expires_on": _json(c.manual_expires_on),
        "note": c.note,
    }


def certification_snapshot(c: Certification) -> Snapshot:
    return {
        "name": c.name,
        "short_name": c.short_name,
        "kind": _json(c.kind),
        "description": c.description,
        "validity_mode": _json(c.validity_mode),
        "validity_months": c.validity_months,
        "warn_days": c.warn_days,
        "sort_order": c.sort_order,
        "is_active": c.is_active,
    }


def position_snapshot(p: Position) -> Snapshot:
    return {
        "name": p.name,
        "description": p.description,
        "certifications": sorted(c.name for c in p.certifications),
    }


def user_snapshot(u: User) -> Snapshot:
    return {
        "username": u.username,
        "email": u.email,
        "display_name": u.display_name,
        "role": _json(u.role),
        "is_active": u.is_active,
        "totp_enabled": u.totp_enabled,
    }


def diff(before: Snapshot, after: Snapshot) -> dict[str, list[Any]]:
    """Returns the fields whose values differ, each with the old and the new value."""
    return {
        key: [before.get(key), after.get(key)]
        for key in sorted(before.keys() | after.keys())
        if before.get(key) != after.get(key)
    }


def record(
    db: Session,
    actor: User,
    entity_type: EntityType,
    entity_id: int,
    label: str,
    action: Action,
    *,
    before: Snapshot | None = None,
    after: Snapshot | None = None,
    member_id: int | None = None,
) -> AuditEntry | None:
    """
    Adds an audit entry to the session without committing, so it is saved together with the
    change it describes. Updates store only changed fields and are skipped when nothing changed.
    Creates store the new state, deletes the old state. Label and user name are copied, so
    entries stay readable after the object or the user is gone.
    """
    if action == Action.UPDATE:
        changes: dict[str, Any] = diff(before or {}, after or {})
        if not changes:
            return None
    elif action == Action.CREATE:
        changes = dict(after or {})
    else:
        changes = dict(before or {})
    entry = AuditEntry(
        user_id=actor.id,
        user_name=actor.display_name,
        entity_type=entity_type.value,
        entity_id=entity_id,
        entity_label=label,
        member_id=member_id,
        action=action.value,
        changes=changes,
    )
    db.add(entry)
    return entry
