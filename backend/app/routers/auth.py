import secrets
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from ..database import get_db
from ..deps import current_user
from ..models import User
from ..ledger_models import AuthSession
from ..schemas import LoginIn, PasswordChangeIn
from ..security import create_token, hash_password, verify_password
from ..config import TOKEN_EXPIRE_MINUTES
from ..runtime_config import SEED_DEMO
from ..utils import abort, ok

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login")
def login(payload: LoginIn, db: Session = Depends(get_db)):
    u = db.query(User).filter_by(username=payload.username).first()
    if not u or not verify_password(payload.password, u.password_hash):
        abort("账号或密码错误", 401)
    db.query(AuthSession).filter(AuthSession.expires_at <= datetime.utcnow()).delete()
    sid = secrets.token_hex(32)
    db.add(
        AuthSession(
            id=sid,
            user_id=u.id,
            expires_at=datetime.utcnow() + timedelta(minutes=TOKEN_EXPIRE_MINUTES),
        )
    )
    db.commit()
    return ok(
        {
            "access_token": create_token(u.username, sid),
            "token_type": "bearer",
            "username": u.username,
            "must_change_password": bool(u.must_change_password),
            "demo": SEED_DEMO,
        }
    )


@router.post("/logout")
def logout(
    request: Request, user: str = Depends(current_user), db: Session = Depends(get_db)
):
    db.query(AuthSession).filter_by(id=request.state.session_id).delete()
    db.commit()
    return ok(None, "已退出登录")


@router.get("/me")
def me(user: str = Depends(current_user), db: Session = Depends(get_db)):
    u = db.query(User).filter_by(username=user).one()
    from ..ledger_models import SystemState

    notice = db.get(SystemState, "upgrade_notice")
    return ok(
        {
            "username": user,
            "must_change_password": bool(u.must_change_password),
            "demo": SEED_DEMO,
            "upgrade_notice": notice.value if notice else None,
        }
    )


@router.put("/password")
def change_password(
    payload: PasswordChangeIn,
    user: str = Depends(current_user),
    db: Session = Depends(get_db),
):
    u = db.query(User).filter_by(username=user).first()
    if not verify_password(payload.old_password, u.password_hash):
        abort("原密码错误")
    if payload.new_password == payload.old_password:
        abort("新密码不能与原密码相同")
    u.password_hash = hash_password(payload.new_password)
    u.must_change_password = 0
    db.query(AuthSession).filter_by(user_id=u.id).delete()
    db.commit()
    return ok(None, "密码已更新，请重新登录")
