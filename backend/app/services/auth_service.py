import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHash
import jwt
from sqlalchemy.orm import Session

from ..config import settings
from ..models import User

# Argon2id password hasher with secure cost parameters
_hasher = PasswordHasher(
    time_cost=2,
    memory_cost=65536,  # 64 MB
    parallelism=1,
    hash_len=32,
    salt_len=16
)

# Common disposable and temporary email domains blocklist
DISPOSABLE_DOMAINS = {
    "mailinator.com", "guerrillamail.com", "tempmail.com", "10minutemail.com",
    "sharklasers.com", "yopmail.com", "trashmail.com", "getairmail.com",
    "dispostable.com", "temp-mail.org", "fakeinbox.com", "throwawaymail.com",
    "burnermail.io", "mohmal.com", "crazymailing.com", "inboxkitten.com"
}

def normalize_email(email: str) -> str:
    """
    Normalizes an email address to prevent duplicate trial abuse:
    - Lowercase & whitespace stripped
    - For Gmail/Googlemail: removes dots in username and strips '+alias' suffixes
    - Normalizes googlemail.com to gmail.com
    """
    clean = email.strip().lower()
    if "@" not in clean:
        return clean
    user, domain = clean.split("@", 1)
    if domain in ("gmail.com", "googlemail.com"):
        domain = "gmail.com"
        user = user.split("+")[0]
        user = user.replace(".", "")
    else:
        # Standard plus-addressing for other domains
        user = user.split("+")[0]
    return f"{user}@{domain}"

def is_disposable_domain(email: str) -> bool:
    clean = email.strip().lower()
    if "@" not in clean:
        return False
    _, domain = clean.split("@", 1)
    return domain in DISPOSABLE_DOMAINS

def hash_password(password: str) -> str:
    return _hasher.hash(password)

def verify_password(hashed_password: str, plain_password: str) -> bool:
    try:
        return _hasher.verify(hashed_password, plain_password)
    except (VerifyMismatchError, InvalidHash):
        return False

def create_access_token(user_id: str, email: str, role: str) -> str:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp())
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def decode_access_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except (jwt.PyJWTError, Exception):
        return None

def generate_verification_token() -> Tuple[str, datetime]:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=24)
    return token, expires_at
