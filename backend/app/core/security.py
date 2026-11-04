from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from .config import settings
from ..database import get_db

bearer = HTTPBearer(auto_error=False)

ROLE_LEVELS = {"viewer": 1, "operator": 2, "admin": 3}


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8")[:72], bcrypt.gensalt()).decode("ascii")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8")[:72], hashed.encode("ascii"))
    except Exception:
        return False


def create_access_token(user_id: int, username: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + settings.access_token_ttl
    payload = {"sub": str(user_id), "username": username, "role": role, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="登录已失效，请重新登录") from exc


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
):
    from ..models import User

    if credentials is None:
        raise HTTPException(status_code=401, detail="未登录")
    payload = decode_token(credentials.credentials)
    user = db.get(User, int(payload.get("sub", "0")))
    if user is None or not user.enabled:
        raise HTTPException(status_code=401, detail="用户不存在或已被禁用")
    return user


def require_role(minimum: str):
    def checker(user=Depends(get_current_user)):
        if ROLE_LEVELS.get(user.role, 0) < ROLE_LEVELS.get(minimum, 99):
            raise HTTPException(status_code=403, detail="权限不足")
        return user

    return checker
