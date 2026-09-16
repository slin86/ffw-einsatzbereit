"""User administration (admins only)."""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from einsatzbereit.deps import AdminUser, DbSession
from einsatzbereit.models import User, UserRole
from einsatzbereit.routers.auth import request_password_reset, revoke_all_sessions
from einsatzbereit.schemas import PasswordResetRequest, UserCreate, UserOut, UserUpdate
from einsatzbereit.security import hash_password

router = APIRouter(prefix="/api/users", tags=["users"])


def _get(db: DbSession, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return user


def _active_admin_count(db: DbSession) -> int:
    return len(
        db.scalars(
            select(User.id).where(User.role == UserRole.ADMIN, User.is_active.is_(True))
        ).all()
    )


@router.get("", response_model=list[UserOut])
def list_users(_: AdminUser, db: DbSession) -> list[User]:
    return list(db.scalars(select(User).order_by(User.display_name)))


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(body: UserCreate, _: AdminUser, db: DbSession) -> User:
    user = User(
        email=body.email.lower(),
        display_name=body.display_name,
        role=body.role,
        password_hash=hash_password(body.password),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "E-mail already in use") from exc
    return user


@router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: int, body: UserUpdate, admin: AdminUser, db: DbSession) -> User:
    user = _get(db, user_id)
    demotes_admin = user.role == UserRole.ADMIN and (
        (body.role is not None and body.role != UserRole.ADMIN) or body.is_active is False
    )
    if demotes_admin and _active_admin_count(db) <= 1:
        raise HTTPException(status.HTTP_409_CONFLICT, "The last active admin cannot be removed")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    if body.is_active is False or (body.role is not None and user.id != admin.id):
        revoke_all_sessions(db, user)
    db.commit()
    return user


@router.post("/{user_id}/reset-2fa", response_model=UserOut)
def reset_totp(user_id: int, _: AdminUser, db: DbSession) -> User:
    user = _get(db, user_id)
    user.totp_enabled = False
    user.totp_secret = None
    revoke_all_sessions(db, user)
    db.commit()
    return user


@router.post("/{user_id}/send-password-reset", status_code=status.HTTP_202_ACCEPTED)
def send_reset(user_id: int, _: AdminUser, db: DbSession) -> None:
    user = _get(db, user_id)
    request_password_reset(PasswordResetRequest(email=user.email), db)
