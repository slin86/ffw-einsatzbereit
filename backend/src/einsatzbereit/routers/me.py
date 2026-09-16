"""Endpoints for the logged-in user: profile, password, 2FA."""

from fastapi import APIRouter, HTTPException, status

from einsatzbereit.deps import CurrentUser, DbSession
from einsatzbereit.routers.auth import revoke_all_sessions
from einsatzbereit.schemas import (
    PasswordChange,
    TotpCode,
    TotpDisable,
    TotpSetupResponse,
    UserOut,
)
from einsatzbereit.security import (
    hash_password,
    new_totp_secret,
    totp_uri,
    verify_password,
    verify_totp,
)

router = APIRouter(prefix="/api/me", tags=["me"])


@router.get("", response_model=UserOut)
def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)


@router.post("/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(body: PasswordChange, user: CurrentUser, db: DbSession) -> None:
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Current password is wrong")
    user.password_hash = hash_password(body.new_password)
    revoke_all_sessions(db, user)
    db.commit()


@router.post("/totp/setup", response_model=TotpSetupResponse)
def totp_setup(user: CurrentUser, db: DbSession) -> TotpSetupResponse:
    if user.totp_enabled:
        raise HTTPException(status.HTTP_409_CONFLICT, "2FA already enabled")
    user.totp_secret = new_totp_secret()
    db.commit()
    return TotpSetupResponse(
        secret=user.totp_secret, otpauth_uri=totp_uri(user.totp_secret, user.email)
    )


@router.post("/totp/enable", response_model=UserOut)
def totp_enable(body: TotpCode, user: CurrentUser, db: DbSession) -> UserOut:
    if user.totp_enabled or not user.totp_secret:
        raise HTTPException(status.HTTP_409_CONFLICT, "Run setup first")
    if not verify_totp(user.totp_secret, body.code):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid code")
    user.totp_enabled = True
    db.commit()
    return UserOut.model_validate(user)


@router.post("/totp/disable", response_model=UserOut)
def totp_disable(body: TotpDisable, user: CurrentUser, db: DbSession) -> UserOut:
    if not (user.totp_enabled and user.totp_secret):
        raise HTTPException(status.HTTP_409_CONFLICT, "2FA not enabled")
    if not verify_password(body.password, user.password_hash) or not verify_totp(
        user.totp_secret, body.code
    ):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid password or code")
    user.totp_enabled = False
    user.totp_secret = None
    db.commit()
    return UserOut.model_validate(user)
