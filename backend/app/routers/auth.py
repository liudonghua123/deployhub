from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..core.security import create_access_token, get_current_user, verify_password
from ..database import get_db
from ..models import User

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginBody(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(body: LoginBody, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == body.username).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if not user.enabled:
        raise HTTPException(status_code=403, detail="账号已被禁用")
    token = create_access_token(user.id, user.username, user.role)
    return {"token": token, "user": user.to_dict()}


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return user.to_dict()
