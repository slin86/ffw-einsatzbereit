"""Certifications (Nachweise) and positions (Funktionen). Read: all users, write: admins."""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from einsatzbereit.deps import AdminUser, CurrentUser, DbSession
from einsatzbereit.models import Certification, Completion, Position
from einsatzbereit.schemas import CertificationIn, CertificationOut, PositionIn, PositionOut
from einsatzbereit.services import audit
from einsatzbereit.services.audit import Action, EntityType

router = APIRouter(prefix="/api", tags=["catalog"])


def _flush(db: DbSession) -> None:
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Name already in use") from exc


# --- Certifications ---------------------------------------------------------


def _get_cert(db: DbSession, cert_id: int) -> Certification:
    cert = db.get(Certification, cert_id)
    if cert is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Certification not found")
    return cert


@router.get("/certifications", response_model=list[CertificationOut])
def list_certifications(_: CurrentUser, db: DbSession) -> list[Certification]:
    return list(
        db.scalars(select(Certification).order_by(Certification.sort_order, Certification.name))
    )


@router.post(
    "/certifications", response_model=CertificationOut, status_code=status.HTTP_201_CREATED
)
def create_certification(body: CertificationIn, admin: AdminUser, db: DbSession) -> Certification:
    cert = Certification(**body.model_dump())
    db.add(cert)
    _flush(db)
    audit.record(
        db,
        admin,
        EntityType.CERTIFICATION,
        cert.id,
        cert.name,
        Action.CREATE,
        after=audit.certification_snapshot(cert),
    )
    db.commit()
    return cert


@router.put("/certifications/{cert_id}", response_model=CertificationOut)
def update_certification(
    cert_id: int, body: CertificationIn, admin: AdminUser, db: DbSession
) -> Certification:
    cert = _get_cert(db, cert_id)
    before = audit.certification_snapshot(cert)
    for k, v in body.model_dump().items():
        setattr(cert, k, v)
    _flush(db)
    audit.record(
        db,
        admin,
        EntityType.CERTIFICATION,
        cert.id,
        cert.name,
        Action.UPDATE,
        before=before,
        after=audit.certification_snapshot(cert),
    )
    db.commit()
    return cert


@router.delete("/certifications/{cert_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_certification(cert_id: int, admin: AdminUser, db: DbSession) -> None:
    cert = _get_cert(db, cert_id)
    if db.scalar(select(Completion.id).where(Completion.certification_id == cert_id).limit(1)):
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Certification has completions – deactivate it instead"
        )
    audit.record(
        db,
        admin,
        EntityType.CERTIFICATION,
        cert.id,
        cert.name,
        Action.DELETE,
        before=audit.certification_snapshot(cert),
    )
    db.delete(cert)
    db.commit()


# --- Positions --------------------------------------------------------------


def _get_position(db: DbSession, position_id: int) -> Position:
    pos = db.get(Position, position_id)
    if pos is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Position not found")
    return pos


def _load_certs(db: DbSession, ids: list[int]) -> list[Certification]:
    certs = list(db.scalars(select(Certification).where(Certification.id.in_(ids))))
    if len(certs) != len(set(ids)):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Unknown certification id")
    return certs


@router.get("/positions", response_model=list[PositionOut])
def list_positions(_: CurrentUser, db: DbSession) -> list[Position]:
    return list(db.scalars(select(Position).order_by(Position.name)))


@router.post("/positions", response_model=PositionOut, status_code=status.HTTP_201_CREATED)
def create_position(body: PositionIn, admin: AdminUser, db: DbSession) -> Position:
    pos = Position(
        name=body.name,
        description=body.description,
        certifications=_load_certs(db, body.certification_ids),
    )
    db.add(pos)
    _flush(db)
    audit.record(
        db,
        admin,
        EntityType.POSITION,
        pos.id,
        pos.name,
        Action.CREATE,
        after=audit.position_snapshot(pos),
    )
    db.commit()
    return pos


@router.put("/positions/{position_id}", response_model=PositionOut)
def update_position(
    position_id: int, body: PositionIn, admin: AdminUser, db: DbSession
) -> Position:
    pos = _get_position(db, position_id)
    before = audit.position_snapshot(pos)
    pos.name = body.name
    pos.description = body.description
    pos.certifications = _load_certs(db, body.certification_ids)
    _flush(db)
    audit.record(
        db,
        admin,
        EntityType.POSITION,
        pos.id,
        pos.name,
        Action.UPDATE,
        before=before,
        after=audit.position_snapshot(pos),
    )
    db.commit()
    return pos


@router.delete("/positions/{position_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_position(position_id: int, admin: AdminUser, db: DbSession) -> None:
    pos = _get_position(db, position_id)
    audit.record(
        db,
        admin,
        EntityType.POSITION,
        pos.id,
        pos.name,
        Action.DELETE,
        before=audit.position_snapshot(pos),
    )
    db.delete(pos)
    db.commit()
