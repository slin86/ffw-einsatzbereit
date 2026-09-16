"""Login, MFA, token refresh, logout and password reset."""

import uuid
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Cookie, HTTPException, Response, status
from sqlalchemy import select, update

from einsatzbereit.config import get_settings
from einsatzbereit.deps import DbSession
from einsatzbereit.mailer import send_mail
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

router = APIRouter(prefix="/api/auth", tags=["auth"])

REFRESH_COOKIE = "eb_refresh"
COOKIE_PATH = "/api/auth"

_INVALID = HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")


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
    s = get_settings()
    user.failed_logins += 1
    if user.failed_logins >= s.max_failed_logins:
        user.locked_until = now_utc() + timedelta(minutes=s.lockout_minutes)
        user.failed_logins = 0
    db.commit()


def _is_locked(user: User) -> bool:
    return user.locked_until is not None and ensure_aware(user.locked_until) > now_utc()


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, response: Response, db: DbSession) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if user is None:
        verify_password(body.password, hash_password("timing-equalizer"))
        raise _INVALID
    if not user.is_active or _is_locked(user):
        raise _INVALID
    if not verify_password(body.password, user.password_hash):
        _register_failure(db, user)
        raise _INVALID
    user.failed_logins = 0
    db.commit()
    if user.totp_enabled:
        return TokenResponse(
            mfa_required=True, mfa_token=create_jwt(user.id, "mfa", user.token_version)
        )
    return _issue_tokens(db, response, user)


@router.post("/login/mfa", response_model=TokenResponse)
def login_mfa(body: MfaLoginRequest, response: Response, db: DbSession) -> TokenResponse:
    decoded = decode_jwt(body.mfa_token, "mfa")
    if decoded is None:
        raise _INVALID
    user = db.get(User, decoded[0])
    if user is None or not user.is_active or _is_locked(user) or user.token_version != decoded[1]:
        raise _INVALID
    if not (user.totp_enabled and user.totp_secret and verify_totp(user.totp_secret, body.code)):
        _register_failure(db, user)
        raise _INVALID
    return _issue_tokens(db, response, user)


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    response: Response,
    db: DbSession,
    eb_refresh: Annotated[str | None, Cookie()] = None,
) -> TokenResponse:
    if not eb_refresh:
        raise _INVALID
    token = db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == hash_opaque_token(eb_refresh))
    )
    if token is None:
        raise _INVALID
    now = now_utc()
    if token.revoked_at is not None:
        # Reuse of a rotated token: assume theft, revoke the whole family.
        db.execute(
            update(RefreshToken)
            .where(RefreshToken.family_id == token.family_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        db.commit()
        raise _INVALID
    if ensure_aware(token.expires_at) < now:
        raise _INVALID
    user = db.get(User, token.user_id)
    if user is None or not user.is_active:
        raise _INVALID
    token.revoked_at = now
    return _issue_tokens(db, response, user, family_id=token.family_id)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response, db: DbSession, eb_refresh: Annotated[str | None, Cookie()] = None
) -> None:
    if eb_refresh:
        token = db.scalar(
            select(RefreshToken).where(RefreshToken.token_hash == hash_opaque_token(eb_refresh))
        )
        if token is not None:
            db.execute(
                update(RefreshToken)
                .where(RefreshToken.family_id == token.family_id, RefreshToken.revoked_at.is_(None))
                .values(revoked_at=now_utc())
            )
            db.commit()
    response.delete_cookie(REFRESH_COOKIE, path=COOKIE_PATH)


@router.post("/password-reset/request", status_code=status.HTTP_202_ACCEPTED)
def request_password_reset(body: PasswordResetRequest, db: DbSession) -> None:
    """Always returns 202 so that registered e-mail addresses cannot be enumerated."""
    s = get_settings()
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if user is None or not user.is_active:
        return
    # Throttle: at most one mail per user within the cooldown window.
    recent = db.scalar(
        select(PasswordResetToken.id).where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.created_at > now_utc() - timedelta(minutes=s.reset_cooldown_minutes),
        )
    )
    if recent is not None:
        return
    # Only the newest link is valid.
    db.execute(
        update(PasswordResetToken)
        .where(PasswordResetToken.user_id == user.id, PasswordResetToken.used_at.is_(None))
        .values(used_at=now_utc())
    )
    raw = new_opaque_token()
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=hash_opaque_token(raw),
            expires_at=now_utc() + timedelta(minutes=s.password_reset_minutes),
        )
    )
    db.commit()
    link = f"{s.public_base_url.rstrip('/')}/passwort-neu?token={raw}"
    send_mail(
        user.email,
        "Einsatzbereit: Passwort zurücksetzen",
        f"Hallo {user.display_name},\n\n"
        f"über diesen Link kannst du ein neues Passwort vergeben "
        f"(gültig für {s.password_reset_minutes} Minuten):\n\n{link}\n\n"
        "Falls du das nicht angefordert hast, ignoriere diese Mail.\n",
    )


@router.post("/password-reset/confirm", status_code=status.HTTP_204_NO_CONTENT)
def confirm_password_reset(body: PasswordResetConfirm, db: DbSession) -> None:
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


def revoke_all_sessions(db: DbSession, user: User) -> None:
    """Invalidate outstanding access tokens and all refresh tokens of a user (no commit)."""
    user.token_version += 1
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now_utc())
    )
