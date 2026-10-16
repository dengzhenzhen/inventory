from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import current_user
from ..models import User
from ..schemas import LoginIn, PasswordChangeIn
from ..security import create_token, hash_password, verify_password
from ..utils import abort, ok

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login")
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(username=payload.username).first()
    if not user or not verify_password(payload.password, user.password_hash):
        abort("账号或密码错误", 401)
    return ok({
        "access_token": create_token(user.username),
        "token_type": "bearer",
        "username": user.username,
    }, "登录成功")


@router.post("/logout")
def logout(user: str = Depends(current_user)):
    return ok(None, "已退出登录")


@router.get("/me")
def me(user: str = Depends(current_user)):
    return ok({"username": user})


@router.put("/password")
def change_password(payload: PasswordChangeIn, user: str = Depends(current_user), db: Session = Depends(get_db)):
    u = db.query(User).filter_by(username=user).first()
    if not u or not verify_password(payload.old_password, u.password_hash):
        abort("原密码错误")
    u.password_hash = hash_password(payload.new_password)
    db.commit()
    return ok(None, "密码已更新")
