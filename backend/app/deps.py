"""Require a live server-side session and enforce first password change."""

from datetime import datetime
from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session
import jwt
from .database import get_db
from .ledger_models import AuthSession
from .models import User
from .security import decode_token


def current_user(
    request: Request,
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "未登录")
    try:
        payload = decode_token(authorization.split(" ", 1)[1].strip())
    except jwt.PyJWTError:
        raise HTTPException(401, "登录凭证无效或已过期")
    session = db.get(AuthSession, payload.get("sid", ""))
    user = db.get(User, session.user_id) if session else None
    if (
        not session
        or session.expires_at <= datetime.utcnow()
        or not user
        or payload.get("sub") != user.username
    ):
        raise HTTPException(401, "登录凭证已失效")
    if user.must_change_password and request.url.path not in (
        "/api/auth/me",
        "/api/auth/password",
        "/api/auth/logout",
    ):
        raise HTTPException(403, "请先修改初始密码")
    request.state.session_id = session.id
    return user.username
