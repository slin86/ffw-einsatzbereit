import uuid
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Cookie, HTTPException, Response, status
from sqlalchemy import select, update

from einsatzbereit.config import get_settings
from einsatzbereit.deps import DbSession
from einsatzbereit.models import PasswordResetToken, RefreshToken, User
from einsatzbereit.schemas import (
    LoginRequest,
    MfaLoginRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    TokenResponse,
)
from einsatzbereit.security import (
    create_jwt,
    decode_jwt,
    ensure_aware,
    hash_opaque_token,
    hash_password,
    new_opaque_token,
    now_utc,
    verify_password,
    verify_totp,
)
from einsatzbereit.services.accounts import revoke_all_sessions, send_password_reset

router = APIRouter(prefix="/api/auth", tags=["auth"])

REFRESH_COOKIE = "eb_refresh"
COOKIE_PATH = "/api/auth"
_TIMING_DUMMY_HASH = hash_password("timing-equalizer")


def _invalid() -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")


def _set_refresh_cookie(response: Response, token: str) -> None:
    s = get_settings()
    response.set_cookie(
        REFRESH_COOKIE,
        token,
        max_age=s.refresh_token_days * 86400,
        httponly=True,
        secure=s.cookie_secure,
        samesite="strict",
        path=COOKIE_PATH,
    )


def _issue_tokens(
    db: DbSession, response: Response, user: User, family_id: str | None = None
) -> TokenResponse:
    """
    Creates a new refresh token, stores only its hash, sets it as an http only cookie and returns
    a fresh access token. Passing a family id keeps the new token in the rotation chain of an
    existing login.
    """
    s = get_settings()
    raw = new_opaque_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_opaque_token(raw),
            family_id=family_id or str(uuid.uuid4()),
            expires_at=now_utc() + timedelta(days=s.refresh_token_days),
        )
    )
    db.commit()
    _set_refresh_cookie(response, raw)
    return TokenResponse(access_token=create_jwt(user.id, "access", user.token_version))


def _register_failure(db: DbSession, user: User) -> None:
    """
    Counts a failed login attempt. After the configured number of failures the account is locked
    for a while and the counter starts again.
    """
    s = get_settings()
    user.failed_logins += 1
    if user.failed_logins >= s.max_failed_logins:
        user.locked_until = now_utc() + timedelta(minutes=s.lockout_minutes)
        user.failed_logins = 0
    db.commit()


def _can_log_in(user: User | None) -> bool:
    if user is None or not user.is_active:
        return False
    return user.locked_until is None or ensure_aware(user.locked_until) <= now_utc()


def _find_refresh_token(db: DbSession, raw: str) -> RefreshToken | None:
    return db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_opaque_token(raw)))


def _revoke_family(db: DbSession, family_id: str) -> None:
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now_utc())
    )
    db.commit()


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, response: Response, db: DbSession) -> TokenResponse:
    """
    Checks email and password. Unknown addresses still run a password hash, so response times do
    not reveal which accounts exist. Users with two factor authentication get a short lived MFA
    token instead of access tokens.
    """
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if user is None:
        verify_password(body.password, _TIMING_DUMMY_HASH)
        raise _invalid()
    if not _can_log_in(user):
        raise _invalid()
    if not verify_password(body.password, user.password_hash):
        _register_failure(db, user)
        raise _invalid()
    user.failed_logins = 0
    db.commit()
    if user.totp_enabled:
        mfa_token = create_jwt(user.id, "mfa", user.token_version)
        return TokenResponse(mfa_required=True, mfa_token=mfa_token)
    return _issue_tokens(db, response, user)


@router.post("/login/mfa", response_model=TokenResponse)
def login_mfa(body: MfaLoginRequest, response: Response, db: DbSession) -> TokenResponse:
    """
    Second login step for users with two factor authentication. Accepts the MFA token from the
    first step together with a TOTP code and issues access and refresh tokens. Wrong codes count
    as failed logins.
    """
    decoded = decode_jwt(body.mfa_token, "mfa")
    if decoded is None:
        raise _invalid()
    user_id, version = decoded
    user = db.get(User, user_id)
    if user is None or not _can_log_in(user) or user.token_version != version:
        raise _invalid()
    if not (user.totp_enabled and user.totp_secret and verify_totp(user.totp_secret, body.code)):
        _register_failure(db, user)
        raise _invalid()
    return _issue_tokens(db, response, user)


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    response: Response,
    db: DbSession,
    eb_refresh: Annotated[str | None, Cookie()] = None,
) -> TokenResponse:
    """
    Exchanges the refresh cookie for a new access token and rotates the refresh token. If an
    already rotated token is presented again, the whole token family is revoked because the token
    was most likely stolen.
    """
    token = _find_refresh_token(db, eb_refresh) if eb_refresh else None
    if token is None:
        raise _invalid()
    if token.revoked_at is not None:
        _revoke_family(db, token.family_id)
        raise _invalid()
    if ensure_aware(token.expires_at) < now_utc():
        raise _invalid()
    user = db.get(User, token.user_id)
    if user is None or not user.is_active:
        raise _invalid()
    token.revoked_at = now_utc()
    return _issue_tokens(db, response, user, family_id=token.family_id)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response, db: DbSession, eb_refresh: Annotated[str | None, Cookie()] = None
) -> None:
    token = _find_refresh_token(db, eb_refresh) if eb_refresh else None
    if token is not None:
        _revoke_family(db, token.family_id)
    response.delete_cookie(REFRESH_COOKIE, path=COOKIE_PATH)


@router.post("/password-reset/request", status_code=status.HTTP_202_ACCEPTED)
def request_password_reset(body: PasswordResetRequest, db: DbSession) -> None:
    """
    Always answers with status 202, so nobody can find out which email addresses are registered.
    """
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if user is not None and user.is_active:
        send_password_reset(db, user)


@router.post("/password-reset/confirm", status_code=status.HTTP_204_NO_CONTENT)
def confirm_password_reset(body: PasswordResetConfirm, db: DbSession) -> None:
    """
    Sets a new password with a valid reset token. The token works only once, the lockout is
    cleared and all existing sessions of the user are revoked.
    """
    invalid = HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired token")
    token = db.scalar(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == hash_opaque_token(body.token)
        )
    )
    now = now_utc()
    if token is None or token.used_at is not None or ensure_aware(token.expires_at) < now:
        raise invalid
    user = db.get(User, token.user_id)
    if user is None or not user.is_active:
        raise invalid
    token.used_at = now
    user.password_hash = hash_password(body.new_password)
    user.failed_logins = 0
    user.locked_until = None
    revoke_all_sessions(db, user)
    db.commit()
