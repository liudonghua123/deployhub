from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..core.security import get_current_user, hash_password, require_role
from ..database import get_db
from ..models import User

router = APIRouter(prefix="/api/users", tags=["users"])

ROLE_LEVELS = {"viewer": 1, "operator": 2, "admin": 3}


class UserBody(BaseModel):
    username: str
    password: str = ""
    role: str = "viewer"
    enabled: bool = True


@router.get("")
def list_users(db: Session = Depends(get_db), user: User = Depends(require_role("viewer"))):
    return [u.to_dict() for u in db.query(User).order_by(User.id).all()]


@router.post("")
def create_user(body: UserBody, db: Session = Depends(get_db), user: User = Depends(require_role("admin"))):
    import re

    name = (body.username or "").strip()
    if not re.fullmatch(r"[a-zA-Z0-9_]{2,32}", name):
        raise HTTPException(status_code=400, detail="用户名只能包含字母、数字、下划线（2-32位）")
    if db.query(User).filter(User.username == name).first():
        raise HTTPException(status_code=400, detail="用户名已存在")
    if body.role not in ROLE_LEVELS:
        raise HTTPException(status_code=400, detail="无效角色")
    if len(body.password) < 6:
        raise HTTPException(status_code=400, detail="密码至少 6 位")
    u = User(username=name, password_hash=hash_password(body.password), role=body.role, enabled=body.enabled)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u.to_dict()


@router.put("/{user_id}")
def update_user(user_id: int, body: UserBody, db: Session = Depends(get_db), user: User = Depends(require_role("admin"))):
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")
    if body.role not in ROLE_LEVELS:
        raise HTTPException(status_code=400, detail="无效角色")
    # cannot lock yourself out: demote/disable self, or demote last admin
    if target.id == user.id:
        if body.role != "admin":
            raise HTTPException(status_code=400, detail="不能修改自己的角色")
        if not body.enabled:
            raise HTTPException(status_code=400, detail="不能禁用自己的账号")
    if target.username == "admin" and body.role != "admin":
        raise HTTPException(status_code=400, detail="不能降级内置管理员")
    target.role = body.role
    target.enabled = body.enabled
    if body.password:
        if len(body.password) < 6:
            raise HTTPException(status_code=400, detail="密码至少 6 位")
        target.password_hash = hash_password(body.password)
    db.commit()
    return target.to_dict()


@router.delete("/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), user: User = Depends(require_role("admin"))):
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")
    if target.id == user.id:
        raise HTTPException(status_code=400, detail="不能删除自己")
    if target.username == "admin":
        raise HTTPException(status_code=400, detail="不能删除内置管理员")
    db.delete(target)
    db.commit()
    return {"message": "用户已删除"}


class PasswordBody(BaseModel):
    old_password: str
    new_password: str


@router.post("/change-password")
def change_password(body: PasswordBody, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    from ..core.security import verify_password

    if not verify_password(body.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="原密码错误")
    if len(body.new_password) < 6:
        raise HTTPException(status_code=400, detail="新密码至少 6 位")
    user.password_hash = hash_password(body.new_password)
    db.commit()
    return {"message": "密码已修改"}
