import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import jwt
import pyotp
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from einsatzbereit.config import get_settings

_hasher = PasswordHasher()

TokenType = Literal["access", "mfa"]


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def now_utc() -> datetime:
    return datetime.now(UTC)


def create_jwt(user_id: int, token_type: TokenType, token_version: int) -> str:
    s = get_settings()
    minutes = {"access": s.access_token_minutes, "mfa": s.mfa_token_minutes}[token_type]
    now = now_utc()
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "typ": token_type,
        "ver": token_version,
        "iss": s.jwt_issuer,
        "iat": now,
        "exp": now + timedelta(minutes=minutes),
    }
    return jwt.encode(payload, s.jwt_secret, algorithm="HS256")


def decode_jwt(token: str, expected_type: TokenType) -> tuple[int, int] | None:
    """
    Validates signature, issuer, expiry and token type. Returns the user id and the token
    version, or None for any invalid token.
    """
    s = get_settings()
    try:
        payload = jwt.decode(
            token,
            s.jwt_secret,
            algorithms=["HS256"],
            issuer=s.jwt_issuer,
            options={"require": ["exp", "sub", "typ"]},
        )
    except jwt.PyJWTError:
        return None
    if payload.get("typ") != expected_type:
        return None
    return int(payload["sub"]), int(payload.get("ver", 0))


def new_opaque_token() -> str:
    return secrets.token_urlsafe(32)


def hash_opaque_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def new_totp_secret() -> str:
    return str(pyotp.random_base32())


def totp_uri(secret: str, account: str) -> str:
    return str(
        pyotp.TOTP(secret).provisioning_uri(name=account, issuer_name=get_settings().totp_issuer)
    )


def verify_totp(secret: str, code: str) -> bool:
    return bool(pyotp.TOTP(secret).verify(code.strip(), valid_window=1))


def ensure_aware(dt: datetime) -> datetime:
    """
    Adds the UTC time zone to naive datetimes. SQLite returns naive values, PostgreSQL returns
    aware ones.
    """
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
