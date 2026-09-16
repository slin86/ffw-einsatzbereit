"""Startup tasks."""

import logging

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from einsatzbereit.config import get_settings
from einsatzbereit.models import User, UserRole
from einsatzbereit.security import hash_password

log = logging.getLogger(__name__)


def ensure_initial_admin(db: Session) -> None:
    """Create the first admin from env vars if the user table is empty."""
    s = get_settings()
    if db.scalar(select(func.count()).select_from(User)):
        return
    if not (s.initial_admin_email and s.initial_admin_password):
        log.warning("No users exist and EB_INITIAL_ADMIN_* is not set – nobody can log in.")
        return
    db.add(
        User(
            email=s.initial_admin_email.lower(),
            display_name="Administrator",
            password_hash=hash_password(s.initial_admin_password),
            role=UserRole.ADMIN,
        )
    )
    db.commit()
    log.info("Initial admin %s created", s.initial_admin_email)
