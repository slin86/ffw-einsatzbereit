"""Certifications (Nachweise) and positions (Funktionen). Read: all users, write: admins."""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from einsatzbereit.deps import AdminUser, CurrentUser, DbSession
from einsatzbereit.models import Certification, Completion, Position
from einsatzbereit.schemas import CertificationIn, CertificationOut, PositionIn, PositionOut

router = APIRouter(prefix="/api", tags=["catalog"])


def _commit(db: DbSession, conflict_msg: str) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, conflict_msg) from exc


# --- Certifications ---------------------------------------------------------


@router.get("/certifications", response_model=list[CertificationOut])
def list_certifications(_: CurrentUser, db: DbSession) -> list[Certification]:
    return list(
        db.scalars(select(Certification).order_by(Certification.sort_order, Certification.name))
    )


@router.post(
    "/certifications", response_model=CertificationOut, status_code=status.HTTP_201_CREATED
)
def create_certification(body: CertificationIn, _: AdminUser, db: DbSession) -> Certification:
    cert = Certification(**body.model_dump())
    db.add(cert)
    _commit(db, "Name already in use")
    return cert


@router.put("/certifications/{cert_id}", response_model=CertificationOut)
def update_certification(
    cert_id: int, body: CertificationIn, _: AdminUser, db: DbSession
) -> Certification:
    cert = db.get(Certification, cert_id)
    if cert is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Certification not found")
    for k, v in body.model_dump().items():
        setattr(cert, k, v)
    _commit(db, "Name already in use")
    return cert


@router.delete("/certifications/{cert_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_certification(cert_id: int, _: AdminUser, db: DbSession) -> None:
    cert = db.get(Certification, cert_id)
    if cert is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Certification not found")
    if db.scalar(select(Completion.id).where(Completion.certification_id == cert_id).limit(1)):
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Certification has completions – deactivate it instead"
        )
    db.delete(cert)
    db.commit()


# --- Positions --------------------------------------------------------------


def _load_certs(db: DbSession, ids: list[int]) -> list[Certification]:
    certs = list(db.scalars(select(Certification).where(Certification.id.in_(ids))))
    if len(certs) != len(set(ids)):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Unknown certification id")
    return certs


@router.get("/positions", response_model=list[PositionOut])
def list_positions(_: CurrentUser, db: DbSession) -> list[Position]:
    return list(db.scalars(select(Position).order_by(Position.name)))


@router.post("/positions", response_model=PositionOut, status_code=status.HTTP_201_CREATED)
def create_position(body: PositionIn, _: AdminUser, db: DbSession) -> Position:
    pos = Position(
        name=body.name,
        description=body.description,
        certifications=_load_certs(db, body.certification_ids),
    )
    db.add(pos)
    _commit(db, "Name already in use")
    return pos


@router.put("/positions/{position_id}", response_model=PositionOut)
def update_position(position_id: int, body: PositionIn, _: AdminUser, db: DbSession) -> Position:
    pos = db.get(Position, position_id)
    if pos is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Position not found")
    pos.name = body.name
    pos.description = body.description
    pos.certifications = _load_certs(db, body.certification_ids)
    _commit(db, "Name already in use")
    return pos


@router.delete("/positions/{position_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_position(position_id: int, _: AdminUser, db: DbSession) -> None:
    pos = db.get(Position, position_id)
    if pos is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Position not found")
    db.delete(pos)
    db.commit()
