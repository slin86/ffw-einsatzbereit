from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from einsatzbereit.deps import AdminUser, DbSession
from einsatzbereit.models import User, UserRole
from einsatzbereit.schemas import UserCreate, UserOut, UserUpdate
from einsatzbereit.security import hash_password
from einsatzbereit.services import audit
from einsatzbereit.services.accounts import revoke_all_sessions, send_password_reset
from einsatzbereit.services.audit import Action, EntityType

router = APIRouter(prefix="/api/users", tags=["users"])


def _flush(db: DbSession) -> None:
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Username or e-mail already in use") from exc


def _get(db: DbSession, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return user


def _active_admin_count(db: DbSession) -> int:
    stmt = select(func.count()).where(User.role == UserRole.ADMIN, User.is_active.is_(True))
    return db.scalar(stmt) or 0


@router.get("", response_model=list[UserOut])
def list_users(_: AdminUser, db: DbSession) -> list[User]:
    return list(db.scalars(select(User).order_by(User.display_name)))


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(body: UserCreate, admin: AdminUser, db: DbSession) -> User:
    user = User(
        username=body.username,
        email=body.email.lower(),
        display_name=body.display_name,
        role=body.role,
        password_hash=hash_password(body.password),
        is_active=True,
        totp_enabled=False,
    )
    db.add(user)
    _flush(db)
    audit.record(
        db,
        admin,
        EntityType.USER,
        user.id,
        user.display_name,
        Action.CREATE,
        after=audit.user_snapshot(user),
    )
    db.commit()
    return user


@router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: int, body: UserUpdate, admin: AdminUser, db: DbSession) -> User:
    """
    Changes username, display name, role or active flag of a user. The last active admin cannot be
    demoted or deactivated. Deactivation and role changes of other users revoke their sessions, so
    the change takes effect immediately.
    """
    user = _get(db, user_id)
    demotes_admin = user.role == UserRole.ADMIN and (
        (body.role is not None and body.role != UserRole.ADMIN) or body.is_active is False
    )
    if demotes_admin and _active_admin_count(db) <= 1:
        raise HTTPException(status.HTTP_409_CONFLICT, "The last active admin cannot be removed")
    before = audit.user_snapshot(user)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    _flush(db)
    if body.is_active is False or (body.role is not None and user.id != admin.id):
        revoke_all_sessions(db, user)
    audit.record(
        db,
        admin,
        EntityType.USER,
        user.id,
        user.display_name,
        Action.UPDATE,
        before=before,
        after=audit.user_snapshot(user),
    )
    db.commit()
    return user


@router.post("/{user_id}/reset-2fa", response_model=UserOut)
def reset_totp(user_id: int, admin: AdminUser, db: DbSession) -> User:
    """
    Removes two factor authentication of a user who lost the device and signs that user out
    everywhere.
    """
    user = _get(db, user_id)
    before = audit.user_snapshot(user)
    user.totp_enabled = False
    user.totp_secret = None
    revoke_all_sessions(db, user)
    audit.record(
        db,
        admin,
        EntityType.USER,
        user.id,
        user.display_name,
        Action.UPDATE,
        before=before,
        after=audit.user_snapshot(user),
    )
    db.commit()
    return user


@router.post("/{user_id}/send-password-reset", status_code=status.HTTP_202_ACCEPTED)
def send_reset(user_id: int, _: AdminUser, db: DbSession) -> None:
    user = _get(db, user_id)
    if not user.is_active:
        raise HTTPException(status.HTTP_409_CONFLICT, "User is deactivated")
    send_password_reset(db, user)
