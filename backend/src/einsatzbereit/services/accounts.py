"""Session revocation and password reset mails."""

from datetime import timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from einsatzbereit.config import get_settings
from einsatzbereit.mailer import send_mail
from einsatzbereit.models import PasswordResetToken, RefreshToken, User
from einsatzbereit.security import hash_opaque_token, new_opaque_token, now_utc


def revoke_all_sessions(db: Session, user: User) -> None:
    """Invalidate outstanding access tokens and all refresh tokens of a user (no commit)."""
    user.token_version += 1
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now_utc())
    )


def send_password_reset(db: Session, user: User) -> bool:
    """Send a reset link unless one was sent within the cooldown. Returns whether a mail went out.

    A new link invalidates all older, unused links of the user.
    """
    s = get_settings()
    now = now_utc()
    recent = db.scalar(
        select(PasswordResetToken.id).where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.created_at > now - timedelta(minutes=s.reset_cooldown_minutes),
        )
    )
    if recent is not None:
        return False
    db.execute(
        update(PasswordResetToken)
        .where(PasswordResetToken.user_id == user.id, PasswordResetToken.used_at.is_(None))
        .values(used_at=now)
    )
    raw = new_opaque_token()
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=hash_opaque_token(raw),
            expires_at=now + timedelta(minutes=s.password_reset_minutes),
            created_at=now,
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
    return True
