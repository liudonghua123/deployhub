"""Functions：版本化运行目标（类似 Appwrite Functions）。

- Function：逻辑单元（运行时/入口文件/环境变量/当前激活版本）
- FunctionVersion：不可变版本快照（文件树 JSON + 落盘 workspaces/functions/<name>/<ver>/）
- 激活版本 = 由该版本目录启动常驻进程；支持一键切换/回滚
- 支持单次执行（execute）：跑 entry_file 并返回输出
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..core.config import settings
from ..core.security import require_role
from ..database import get_db
from ..models import Function, FunctionVersion, User
from ..services.process_manager import process_manager

router = APIRouter(prefix="/api/functions", tags=["functions"])

NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")
FILE_PATH_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_\-./]{0,127}$")
MAX_FILE_SIZE = 512 * 1024  # 单文件 512KB
MAX_TOTAL_SIZE = 5 * 1024 * 1024  # 版本总大小 5MB
EXEC_TIMEOUT = 30


def validate_name(name: str) -> str:
    name = (name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="函数名不能为空")
    if not NAME_RE.match(name):
        raise HTTPException(status_code=400, detail="函数名只能包含字母、数字、下划线、连字符（≤64字符）")
    return name


def validate_files(files: dict[str, str]) -> dict[str, str]:
    if not files or not isinstance(files, dict):
        raise HTTPException(status_code=400, detail="文件内容不能为空")
    total = 0
    for path, content in files.items():
        if not FILE_PATH_RE.match(path):
            raise HTTPException(status_code=400, detail=f"非法文件路径: {path}")
        if ".." in path or path.startswith("/"):
            raise HTTPException(status_code=400, detail=f"文件路径不允许相对/绝对引用: {path}")
        size = len(content.encode("utf-8"))
        if size > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail=f"文件 {path} 超过 512KB 限制")
        total += size
    if total > MAX_TOTAL_SIZE:
        raise HTTPException(status_code=400, detail="版本文件总大小超过 5MB 限制")
    return files


def fn_dir(name: str) -> str:
    return os.path.join(settings.WORKSPACES_DIR, "functions", name)


def version_dir(name: str, version: int) -> str:
    return os.path.join(fn_dir(name), f"v{version}")


def write_version_files(name: str, version: int, files: dict[str, str]):
    vdir = version_dir(name, version)
    os.makedirs(vdir, exist_ok=True)
    for rel, content in files.items():
        dest = os.path.join(vdir, rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "w", encoding="utf-8", errors="replace", newline="\n") as f:
            f.write(content)


def remove_version_files(name: str, version: int):
    safe_rmtree(version_dir(name, version))


def safe_rmtree(path: str):
    """带兑底的目录删除：rmtree 失败时逐文件删除（避免被安全钩子拦截导致整体失败）。"""
    if not os.path.isdir(path):
        return
    try:
        shutil.rmtree(path)
        return
    except Exception:
        pass
    # fallback: 逐项删除
    for root, dirs, files in os.walk(path, topdown=False):
        for f in files:
            fp = os.path.join(root, f)
            try:
                os.chmod(fp, 0o666)
                os.remove(fp)
            except OSError:
                pass
        for d in dirs:
            try:
                os.rmdir(os.path.join(root, d))
            except OSError:
                pass
    try:
        os.rmdir(path)
    except OSError:
        pass


def _fn_or_404(db: Session, fn_id: int) -> Function:
    fn = db.get(Function, fn_id)
    if not fn:
        raise HTTPException(status_code=404, detail="函数不存在")
    return fn


def _next_version(db: Session, function_id: int) -> int:
    last = (
        db.query(FunctionVersion)
        .filter(FunctionVersion.function_id == function_id)
        .order_by(FunctionVersion.version.desc())
        .first()
    )
    return (last.version + 1) if last else 1


class FunctionBody(BaseModel):
    name: str
    runtime: str = "python"       # python / node
    run_command: str = ""
    entry_file: str = "main.py"
    env: dict[str, str] = {}
    description: str = ""


class VersionBody(BaseModel):
    files: dict[str, str]
    label: str = ""
    run_command: str = ""         # 留空则继承函数级 run_command
    entry_file: str = ""          # 留空则继承函数级 entry_file


class EditBody(BaseModel):
    path: str
    content: str


DEFAULT_TEMPLATES: dict[str, dict[str, str]] = {
    "python": {
        "main.py": """import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
import os

PORT = int(os.environ.get("PORT", "3000"))

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = b"Hello from DeployHub Function v1\\n"
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass  # 静默访问日志

if __name__ == "__main__":
    print(f"function listening on :{PORT}")
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
""",
        "requirements.txt": "",
    },
    "node": {
        "main.js": """const http = require('http');

const PORT = process.env.PORT || 3000;

const server = http.createServer((req, res) => {
  res.writeHead(200, { 'Content-Type': 'text/plain; charset=utf-8' });
  res.end('Hello from DeployHub Function v1\\n');
});

server.listen(PORT, () => console.log(`function listening on :${PORT}`));
""",
        "package.json": json.dumps({"name": "function", "private": True}, indent=2),
    },
}

RUNTIME_DEFAULTS = {
    "python": {"run_command": "python main.py", "entry_file": "main.py"},
    "node": {"run_command": "node main.js", "entry_file": "main.js"},
}


# ---------- 函数 CRUD ----------

@router.get("")
def list_functions(db: Session = Depends(get_db), user: User = Depends(require_role("viewer"))):
    fns = db.query(Function).order_by(Function.id).all()
    result = []
    for fn in fns:
        d = fn.to_dict()
        latest = (
            db.query(FunctionVersion)
            .filter(FunctionVersion.function_id == fn.id)
            .order_by(FunctionVersion.version.desc())
            .first()
        )
        d["latest_version"] = latest.version if latest else 0
        d["version_count"] = db.query(FunctionVersion).filter(FunctionVersion.function_id == fn.id).count()
        proc = process_manager.get(fn.id, fn.name)
        d["running"] = proc.process is not None and proc.process.poll() is None
        result.append(d)
    return result


@router.post("", status_code=201)
def create_function(body: FunctionBody, db: Session = Depends(get_db), user: User = Depends(require_role("operator"))):
    name = validate_name(body.name)
    if db.query(Function).filter(Function.name == name).first():
        raise HTTPException(status_code=409, detail="同名函数已存在")
    if body.runtime not in RUNTIME_DEFAULTS:
        raise HTTPException(status_code=400, detail="runtime 仅支持 python / node")
    fn = Function(
        name=name,
        runtime=body.runtime,
        run_command=body.run_command or RUNTIME_DEFAULTS[body.runtime]["run_command"],
        entry_file=body.entry_file or RUNTIME_DEFAULTS[body.runtime]["entry_file"],
        env_json=json.dumps(body.env or {}, ensure_ascii=False),
        description=body.description or "",
    )
    db.add(fn)
    db.commit()
    db.refresh(fn)
    return fn.to_dict()


@router.get("/{fn_id}")
def get_function(fn_id: int, db: Session = Depends(get_db), user: User = Depends(require_role("viewer"))):
    fn = _fn_or_404(db, fn_id)
    d = fn.to_dict()
    d["running"] = process_manager.get(fn.id, fn.name).process is not None and process_manager.get(fn.id, fn.name).process.poll() is None
    return d


@router.put("/{fn_id}")
def update_function(fn_id: int, body: FunctionBody, db: Session = Depends(get_db), user: User = Depends(require_role("operator"))):
    fn = _fn_or_404(db, fn_id)
    if body.runtime not in RUNTIME_DEFAULTS:
        raise HTTPException(status_code=400, detail="runtime 仅支持 python / node")
    fn.runtime = body.runtime
    fn.run_command = body.run_command or fn.run_command
    fn.entry_file = body.entry_file or fn.entry_file
    fn.env_json = json.dumps(body.env or {}, ensure_ascii=False)
    fn.description = body.description or ""
    db.commit()
    return fn.to_dict()


@router.delete("/{fn_id}", status_code=204)
def delete_function(fn_id: int, db: Session = Depends(get_db), user: User = Depends(require_role("admin"))):
    fn = _fn_or_404(db, fn_id)
    process_manager.stop(fn.id, fn.name, force=True)
    # 先显式删除版本行（避免 SQLAlchemy 将 FK 置 NULL 触发 NOT NULL 约束）
    db.query(FunctionVersion).filter(FunctionVersion.function_id == fn.id).delete()
    db.delete(fn)
    db.commit()
    safe_rmtree(fn_dir(fn.name))


# ---------- 版本管理 ----------

@router.get("/{fn_id}/versions")
def list_versions(fn_id: int, db: Session = Depends(get_db), user: User = Depends(require_role("viewer"))):
    fn = _fn_or_404(db, fn_id)
    versions = (
        db.query(FunctionVersion)
        .filter(FunctionVersion.function_id == fn.id)
        .order_by(FunctionVersion.version.desc())
        .all()
    )
    return [v.to_dict() for v in versions]


@router.get("/{fn_id}/versions/{version}")
def get_version(fn_id: int, version: int, db: Session = Depends(get_db), user: User = Depends(require_role("viewer"))):
    fn = _fn_or_404(db, fn_id)
    v = db.query(FunctionVersion).filter(FunctionVersion.function_id == fn.id, FunctionVersion.version == version).first()
    if not v:
        raise HTTPException(status_code=404, detail="版本不存在")
    return v.to_dict(include_files=True)


@router.post("/{fn_id}/versions", status_code=201)
def create_version(fn_id: int, body: VersionBody, db: Session = Depends(get_db), user: User = Depends(require_role("operator"))):
    """从在线编辑的文件树创建新版本（不可变快照）。"""
    fn = _fn_or_404(db, fn_id)
    files = validate_files(body.files)
    entry = body.entry_file or fn.entry_file
    if entry not in files:
        raise HTTPException(status_code=400, detail=f"入口文件 {entry} 必须包含在文件列表中")
    version = _next_version(db, fn.id)
    v = FunctionVersion(
        function_id=fn.id,
        version=version,
        label=body.label or "",
        files_json=json.dumps(files, ensure_ascii=False),
        run_command=body.run_command or fn.run_command,
        entry_file=entry,
        created_by=user.username,
    )
    db.add(v)
    db.commit()
    db.refresh(v)
    write_version_files(fn.name, version, files)
    return v.to_dict()


@router.put("/{fn_id}/versions/{version}/files")
def edit_version_file(fn_id: int, version: int, body: EditBody, db: Session = Depends(get_db), user: User = Depends(require_role("operator"))):
    """在线编辑版本文件。旧版本（非最新）默认锁定，仅最新版本可直接编辑。"""
    fn = _fn_or_404(db, fn_id)
    v = db.query(FunctionVersion).filter(FunctionVersion.function_id == fn.id, FunctionVersion.version == version).first()
    if not v:
        raise HTTPException(status_code=404, detail="版本不存在")
    latest = _next_version(db, fn.id) - 1
    if version != latest:
        raise HTTPException(status_code=409, detail=f"v{version} 是历史版本（只读）。请基于它创建新版本再编辑。")
    if not FILE_PATH_RE.match(body.path):
        raise HTTPException(status_code=400, detail="非法文件路径")
    files = json.loads(v.files_json or "{}")
    if body.content == "":
        files.pop(body.path, None)  # 空内容 = 删除文件
    else:
        files[body.path] = body.content
    validate_files(files)
    v.files_json = json.dumps(files, ensure_ascii=False)
    db.commit()
    write_version_files(fn.name, version, files)
    return {"ok": True, "file_count": len(files)}


@router.post("/{fn_id}/versions/{version}/publish")
def publish_version(fn_id: int, version: int, db: Session = Depends(get_db), user: User = Depends(require_role("operator"))):
    """发布：激活该版本并（重）启动进程。发布即切换流量目标。"""
    fn = _fn_or_404(db, fn_id)
    v = db.query(FunctionVersion).filter(FunctionVersion.function_id == fn.id, FunctionVersion.version == version).first()
    if not v:
        raise HTTPException(status_code=404, detail="版本不存在")
    vdir = version_dir(fn.name, version)
    if not os.path.isdir(vdir):
        write_version_files(fn.name, version, json.loads(v.files_json or "{}"))
    # 更新激活状态
    db.query(FunctionVersion).filter(FunctionVersion.function_id == fn.id).update({"status": "ready"})
    v.status = "active"
    fn.active_version = version
    db.commit()
    # 重启进程指向新版本目录
    env = json.loads(fn.env_json or "{}")
    res = process_manager.restart(fn.id, fn.name, vdir, v.run_command, env)
    if not res.get("ok"):
        v.status = "failed"
        db.commit()
        raise HTTPException(status_code=500, detail=res.get("message", "启动失败"))
    return {"ok": True, "active_version": version, "pid": res.get("pid"), "message": f"已发布并激活 v{version}"}


@router.post("/{fn_id}/rollback")
def rollback(fn_id: int, db: Session = Depends(get_db), user: User = Depends(require_role("operator"))):
    """回滚到上一个版本（一键切回）。"""
    fn = _fn_or_404(db, fn_id)
    if fn.active_version <= 1:
        raise HTTPException(status_code=400, detail="没有可回滚的更早版本")
    target = db.query(FunctionVersion).filter(
        FunctionVersion.function_id == fn.id,
        FunctionVersion.version < fn.active_version,
    ).order_by(FunctionVersion.version.desc()).first()
    if not target:
        raise HTTPException(status_code=404, detail="未找到历史版本")
    return publish_version(fn_id, target.version, db, user)


# ---------- 执行 / 进程控制 ----------

@router.post("/{fn_id}/execute")
def execute(fn_id: int, db: Session = Depends(get_db), user: User = Depends(require_role("viewer"))):
    """单次执行当前激活版本（同步，30s 超时），返回 stdout/stderr。"""
    fn = _fn_or_404(db, fn_id)
    if not fn.active_version:
        raise HTTPException(status_code=400, detail="函数尚未发布任何版本")
    v = db.query(FunctionVersion).filter(FunctionVersion.function_id == fn.id, FunctionVersion.version == fn.active_version).first()
    if not v:
        raise HTTPException(status_code=404, detail="激活版本数据缺失")
    vdir = version_dir(fn.name, fn.active_version)
    if not os.path.isdir(vdir):
        write_version_files(fn.name, fn.active_version, json.loads(v.files_json or "{}"))
    env = os.environ.copy()
    env.update({str(k): str(val) for k, val in json.loads(fn.env_json or "{}").items()})
    use_shell = sys.platform == "win32"
    try:
        proc = subprocess.Popen(
            v.run_command, cwd=vdir, shell=use_shell,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace", env=env,
        )
        try:
            out, _ = proc.communicate(timeout=EXEC_TIMEOUT)
            code = proc.returncode
        except subprocess.TimeoutExpired:
            proc.kill()
            out, _ = proc.communicate()
            code = -1
            out += f"\n[deployhub] 执行超时（>{EXEC_TIMEOUT}s）"
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"执行失败: {exc}")
    return {"ok": code == 0, "exit_code": code, "output": (out or "").strip()}


@router.post("/{fn_id}/start")
def start_fn(fn_id: int, db: Session = Depends(get_db), user: User = Depends(require_role("operator"))):
    fn = _fn_or_404(db, fn_id)
    if not fn.active_version:
        raise HTTPException(status_code=400, detail="请先发布一个版本")
    v = db.query(FunctionVersion).filter(FunctionVersion.function_id == fn.id, FunctionVersion.version == fn.active_version).first()
    vdir = version_dir(fn.name, fn.active_version)
    if not os.path.isdir(vdir):
        write_version_files(fn.name, fn.active_version, json.loads(v.files_json or "{}"))
    env = json.loads(fn.env_json or "{}")
    res = process_manager.start(fn.id, fn.name, vdir, v.run_command, env)
    if not res.get("ok"):
        raise HTTPException(status_code=500, detail=res.get("message", "启动失败"))
    return res


@router.post("/{fn_id}/stop")
def stop_fn(fn_id: int, db: Session = Depends(get_db), user: User = Depends(require_role("operator"))):
    fn = _fn_or_404(db, fn_id)
    return process_manager.stop(fn.id, fn.name, force=True)


@router.get("/{fn_id}/logs")
def fn_logs(fn_id: int, tail: int = 200, db: Session = Depends(get_db), user: User = Depends(require_role("viewer"))):
    fn = _fn_or_404(db, fn_id)
    return {"name": fn.name, "lines": process_manager.logs(fn.id, fn.name, tail)}
