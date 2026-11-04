from __future__ import annotations

import json
import os
import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..core.security import require_role
from ..database import get_db
from ..models import App, User
from ..services.process_manager import process_manager
from ..services.ports import app_port_map

router = APIRouter(prefix="/api/apps", tags=["apps"])

NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")


def validate_name(name: str):
    name = (name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="应用名不能为空")
    if not NAME_RE.match(name):
        raise HTTPException(
            status_code=400,
            detail="应用名只能包含字母、数字、下划线、连字符，且以字母或数字开头（≤64字符）",
        )
    return name


def validate_command_field(start_command: str):
    if not (start_command or "").strip():
        raise HTTPException(status_code=400, detail="启动命令不能为空")


class AppBody(BaseModel):
    name: str
    repo_url: str = ""
    branch: str = "main"
    deploy_dir: str = ""
    init_command: str = ""
    start_command: str = ""
    env: dict[str, str] = {}
    auto_deploy: bool = True
    description: str = ""


def _app_or_404(db: Session, app_id: int) -> App:
    app = db.get(App, app_id)
    if not app:
        raise HTTPException(status_code=404, detail="应用不存在")
    return app


@router.get("")
def list_apps(db: Session = Depends(get_db), user: User = Depends(require_role("viewer"))):
    apps = db.query(App).order_by(App.id).all()
    status_list = [process_manager.status(a.id, a.name) for a in apps]
    port_map = app_port_map(status_list)
    result = []
    for app, st in zip(apps, status_list):
        d = app.to_dict()
        d["status"] = st
        d["listen_ports"] = sorted({port_map[p] and p for p in port_map if port_map[p] == app.name})
        result.append(d)
    return result


@router.post("")
def create_app(body: AppBody, db: Session = Depends(get_db), user: User = Depends(require_role("operator"))):
    name = validate_name(body.name)
    validate_command_field(body.start_command)
    if db.query(App).filter(App.name == name).first():
        raise HTTPException(status_code=400, detail="应用名已存在")
    app = App(
        name=name,
        repo_url=body.repo_url,
        branch=body.branch,
        deploy_dir=body.deploy_dir,
        init_command=body.init_command,
        start_command=body.start_command,
        env_json=json.dumps(body.env, ensure_ascii=False),
        auto_deploy=body.auto_deploy,
        description=body.description,
    )
    db.add(app)
    db.commit()
    db.refresh(app)
    return app.to_dict()


@router.get("/{app_id}")
def get_app(app_id: int, db: Session = Depends(get_db), user: User = Depends(require_role("viewer"))):
    app = _app_or_404(db, app_id)
    d = app.to_dict()
    d["status"] = process_manager.status(app.id, app.name)
    return d


@router.put("/{app_id}")
def update_app(app_id: int, body: AppBody, db: Session = Depends(get_db), user: User = Depends(require_role("operator"))):
    app = _app_or_404(db, app_id)
    validate_command_field(body.start_command)
    new_name = validate_name(body.name)
    if new_name != app.name and db.query(App).filter(App.name == new_name).first():
        raise HTTPException(status_code=400, detail="应用名已存在")
    for field in ("repo_url", "branch", "deploy_dir", "init_command", "start_command", "auto_deploy", "description"):
        setattr(app, field, getattr(body, field))
    app.name = new_name
    app.env_json = json.dumps(body.env, ensure_ascii=False)
    db.commit()
    return app.to_dict()


@router.delete("/{app_id}")
def delete_app(app_id: int, db: Session = Depends(get_db), user: User = Depends(require_role("admin"))):
    app = _app_or_404(db, app_id)
    process_manager.stop(app.id, app.name, force=True)
    # cascade: remove deployment history first (FK constraint)
    from ..models import Deployment
    db.query(Deployment).filter(Deployment.app_id == app.id).delete()
    db.delete(app)
    db.commit()
    return {"message": f"应用 {app.name} 已删除"}


class ActionBody(BaseModel):
    action: str  # start / stop / restart


@router.post("/{app_id}/action")
def app_action(app_id: int, body: ActionBody, db: Session = Depends(get_db), user: User = Depends(require_role("operator"))):
    app = _app_or_404(db, app_id)
    workdir = app.deploy_dir or os.path.join(".", "workspaces", app.name)
    env = json.loads(app.env_json or "{}")
    if body.action == "start":
        return process_manager.start(app.id, app.name, workdir, app.start_command, env)
    if body.action == "stop":
        return process_manager.stop(app.id, app.name)
    if body.action == "restart":
        return process_manager.restart(app.id, app.name, workdir, app.start_command, env)
    raise HTTPException(status_code=400, detail="未知操作")


class HealthBody(BaseModel):
    port: int
    path: str = "/"



@router.post("/{app_id}/health")
def check_health(app_id: int, body: HealthBody, user: User = Depends(require_role("viewer"))):
    """HTTP health probe: GET http://127.0.0.1:{port}{path} with 3s timeout."""
    import urllib.request
    import urllib.error

    url = f"http://127.0.0.1:{body.port}{body.path}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "DeployHub-Health/1.0"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            return {"ok": True, "status": resp.status, "url": url}
    except urllib.error.HTTPError as e:
        # HTTP error responses still mean the app is alive
        return {"ok": True, "status": e.code, "url": url}
    except Exception as e:
        return {"ok": False, "status": None, "url": url, "error": str(e)[:200]}
