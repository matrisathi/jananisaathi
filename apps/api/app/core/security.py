import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from app.core.config import settings

password_hasher = PasswordHash.recommended()  # argon2, per pwdlib[argon2]


def hash_password(plain: str) -> str:
    return password_hasher.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return password_hasher.verify(plain, hashed)


def create_access_token(*, staff_user_id: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": staff_user_id,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_ttl_minutes),
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def new_refresh_token() -> tuple[str, str]:
    """Returns (opaque_token_for_cookie, sha256_hash_for_storage).

    The refresh token is a random opaque value, not a JWT: only its hash is
    stored, so a leaked database row cannot be replayed as a live token.
    """
    token = secrets.token_urlsafe(48)
    token_hash = hash_refresh_token(token)
    return token, token_hash


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
