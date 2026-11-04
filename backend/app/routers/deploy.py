from __future__ import annotations

import hmac
import hashlib
import json

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from ..core.config import settings
from ..core.security import require_role
from ..database import get_db
from ..models import App, Deployment, User
from ..services.deploy import deploy_pipeline

router = APIRouter(prefix="/api/deploy", tags=["deploy"])


@router.post("/{app_id}")
def deploy_app(app_id: int, db: Session = Depends(get_db), user: User = Depends(require_role("operator"))):
    app = db.get(App, app_id)
    if not app:
        raise HTTPException(status_code=404, detail="应用不存在")
    if not app.start_command:
        raise HTTPException(status_code=400, detail="请先设置启动命令")
    if deploy_pipeline.is_running(app.id):
        raise HTTPException(status_code=409, detail="该应用已有部署任务在进行中，请稍候")
    try:
        dep_id = deploy_pipeline.run_deploy(db, app, trigger=f"手动({user.username})")
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {"deployment_id": dep_id, "message": "部署任务已开始"}


@router.get("/{app_id}/history")
def deploy_history(app_id: int, limit: int = 20, db: Session = Depends(get_db), user: User = Depends(require_role("viewer"))):
    app = db.get(App, app_id)
    if not app:
        raise HTTPException(status_code=404, detail="应用不存在")
    rows = (
        db.query(Deployment)
        .filter(Deployment.app_id == app_id)
        .order_by(Deployment.id.desc())
        .limit(limit)
        .all()
    )
    out = []
    for r in rows:
        d = r.to_dict()
        d["app_name"] = app.name
        out.append(d)
    return out


@router.get("/log/{dep_id}")
def deploy_log(dep_id: int, db: Session = Depends(get_db), user: User = Depends(require_role("viewer"))):
    dep = db.get(Deployment, dep_id)
    if not dep:
        raise HTTPException(status_code=404, detail="部署记录不存在")
    d = dep.to_dict()
    d["log"] = dep.log
    return d


async def _verify_github_signature(payload: bytes, signature: str | None):
    if not settings.GITHUB_WEBHOOK_SECRET:
        return
    if not signature:
        raise HTTPException(status_code=403, detail="缺少签名")
    mac = hmac.new(settings.GITHUB_WEBHOOK_SECRET.encode(), payload, hashlib.sha256)
    expected = "sha256=" + mac.hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=403, detail="签名校验失败")


@router.post("/webhook/{app_name}")
async def github_webhook(app_name: str, request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    await _verify_github_signature(payload, request.headers.get("X-Hub-Signature-256"))
    app = db.query(App).filter(App.name == app_name).first()
    if not app:
        raise HTTPException(status_code=404, detail="应用不存在")
    if not app.auto_deploy:
        return {"message": "该应用未开启自动部署"}
    event = request.headers.get("X-GitHub-Event", "push")
    if event == "ping":
        return {"message": "pong"}
    if event != "push":
        return {"message": f"忽略事件 {event}"}
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="无效的 payload")
    commit = (data.get("after") or "")[:8]
    commit_msg = (data.get("head_commit") or {}).get("message", "")[:200]
    dep_id = deploy_pipeline.run_deploy(db, app, trigger="GitHub webhook", commit=commit, commit_msg=commit_msg)
    return {"deployment_id": dep_id, "message": "webhook 部署已触发"}
