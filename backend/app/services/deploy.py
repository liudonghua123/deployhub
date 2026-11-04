"""Deployment pipeline: clone/pull from GitHub, run init command, (re)start app."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading

from ..core.config import settings
from ..core.timeutil import now_str
from .process_manager import process_manager


class DeployPipeline:
    def __init__(self):
        self._active: set[int] = set()  # app_ids with a running deployment
        self._lock = threading.Lock()

    def is_running(self, app_id: int) -> bool:
        with self._lock:
            return app_id in self._active

    def run_deploy(self, db, app, trigger: str = "manual", commit: str = "", commit_msg: str = "") -> int:
        """Create a Deployment row and run the pipeline in a background thread. Returns deployment id."""
        from ..models import Deployment

        with self._lock:
            if app.id in self._active:
                raise RuntimeError("该应用已有部署任务在进行中，请稍候")
            self._active.add(app.id)
        dep = Deployment(app_id=app.id, commit=commit, commit_msg=commit_msg, status="running", log="")
        db.add(dep)
        db.commit()
        db.refresh(dep)
        threading.Thread(
            target=self._pipeline, args=(app.id, dep.id, app.name, app.repo_url, app.branch,
                                         app.deploy_dir or os.path.join(settings.WORKSPACES_DIR, app.name),
                                         app.init_command, app.start_command,
                                         app.env_json, trigger), daemon=True
        ).start()
        return dep.id

    def _run_step(self, log_lines: list, cwd: str, command: str, env: dict | None = None) -> bool:
        if not command or not command.strip():
            return True
        log_lines.append(f"$ {command}")
        merged = os.environ.copy()
        if env:
            merged.update({str(k): str(v) for k, v in env.items()})
        use_shell = sys.platform == "win32"
        proc = subprocess.Popen(
            command, cwd=cwd if os.path.isdir(cwd) else None, shell=use_shell,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            encoding="utf-8", errors="replace", env=merged,
        )
        for line in iter(proc.stdout.readline, ""):
            if line:
                log_lines.append(line.rstrip("\n"))
        proc.wait()
        if proc.returncode != 0:
            log_lines.append(f"[deployhub] command exited with code {proc.returncode}")
            return False
        return True

    def _pipeline(self, app_id: int, dep_id: int, name: str, repo: str, branch: str,
                  workdir: str, init_cmd: str, start_cmd: str, env_json: str, trigger: str):
        from ..database import SessionLocal
        from ..models import Deployment

        log_lines: list[str] = [f"[deployhub] === 部署 {name} @ {now_str()} (触发: {trigger}) ==="]
        ok = False
        try:
            env = json.loads(env_json or "{}")
            os.makedirs(workdir, exist_ok=True)
            git_dir = os.path.join(workdir, ".git")

            if repo:
                if os.path.isdir(git_dir):
                    log_lines.append(f"$ git pull origin {branch}")
                    ok = self._run_step(log_lines, workdir, f"git pull origin {branch}", env)
                else:
                    log_lines.append(f"$ git clone -b {branch} {repo} .")
                    ok = self._run_step(log_lines, workdir, f'git clone -b {branch} "{repo}" .', env)
                if not ok:
                    raise RuntimeError("git 拉取失败")

            log_lines.append("$ init: " + (init_cmd or "(跳过)"))
            if not self._run_step(log_lines, workdir, init_cmd, env):
                raise RuntimeError("初始化命令失败")

            process_manager.stop(app_id, name, force=True)
            res = process_manager.start(app_id, name, workdir, start_cmd, env)
            if not res.get("ok"):
                raise RuntimeError(res.get("message", "启动失败"))
            log_lines.append(f"[deployhub] 应用已启动 (PID {res.get('pid')})")
            ok = True
        except Exception as exc:
            log_lines.append(f"[deployhub] 部署失败: {exc}")
            ok = False
        finally:
            with self._lock:
                self._active.discard(app_id)
            log_lines.append(f"[deployhub] === {'成功' if ok else '失败'} ===")
            db = SessionLocal()
            try:
                dep = db.get(Deployment, dep_id)
                if dep:
                    dep.status = "success" if ok else "failed"
                    dep.log = "\n".join(log_lines)
                    db.commit()
            finally:
                db.close()


deploy_pipeline = DeployPipeline()
