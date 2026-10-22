"""密码哈希（PBKDF2-SHA256）与 JWT 令牌。"""

import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

import jwt

from .config import ALGORITHM, SECRET_KEY, TOKEN_EXPIRE_MINUTES


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or os.urandom(16).hex()
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000).hex()
    return f"pbkdf2_sha256${salt}${dk}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, salt, dk = stored.split("$")
    except (ValueError, AttributeError):
        return False
    if algo != "pbkdf2_sha256":
        return False
    calc = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), 100_000
    ).hex()
    return hmac.compare_digest(calc, dk)


def create_token(username: str, session_id: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": username, "exp": exp, "sid": session_id},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


def decode_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
