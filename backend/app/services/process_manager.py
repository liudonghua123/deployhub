"""Process manager: runs each app as a subprocess, captures output to ring buffer + log file."""
from __future__ import annotations

import asyncio
import json
import os
import signal
import subprocess
import sys
import threading
import time
from collections import deque
from dataclasses import dataclass, field

from ..core.config import settings


@dataclass
class ManagedProcess:
    app_id: int
    name: str
    process: subprocess.Popen | None = None
    log_buffer: deque = field(default_factory=lambda: deque(maxlen=2000))
    started_at: float = 0.0
    listeners: set = field(default_factory=set)  # asyncio queues for WS fanout

    def snapshot(self) -> dict:
        proc = self.process
        running = proc is not None and proc.poll() is None
        return {
            "app_id": self.app_id,
            "name": self.name,
            "running": running,
            "pid": proc.pid if running else None,
            "exit_code": None if running else (proc.returncode if proc else None),
            "started_at": self.started_at,
            "uptime": int(time.time() - self.started_at) if running else 0,
        }


class ProcessManager:
    def __init__(self):
        self._procs: dict[int, ManagedProcess] = {}
        self._lock = threading.Lock()
        os.makedirs(settings.LOGS_DIR, exist_ok=True)
        os.makedirs(settings.WORKSPACES_DIR, exist_ok=True)

    def get(self, app_id: int, name: str = "") -> ManagedProcess:
        with self._lock:
            mp = self._procs.get(app_id)
            if mp is None:
                mp = ManagedProcess(app_id=app_id, name=name)
                self._procs[app_id] = mp
            return mp

    def log_file(self, name: str) -> str:
        safe = "".join(c for c in name if c.isalnum() or c in "-_.") or "app"
        return os.path.join(settings.LOGS_DIR, f"{safe}.log")

    def _append(self, mp: ManagedProcess, line: str):
        mp.log_buffer.append(line)
        try:
            with open(self.log_file(mp.name), "a", encoding="utf-8", errors="replace") as f:
                f.write(line if line.endswith("\n") else line + "\n")
        except OSError:
            pass
        dead = []
        for q in list(mp.listeners):
            try:
                q.put_nowait(line)
            except Exception:
                dead.append(q)
        for q in dead:
            mp.listeners.discard(q)

    def _pump(self, mp: ManagedProcess, stream, prefix: str = ""):
        for raw in iter(stream.readline, ""):
            if not raw:
                break
            self._append(mp, prefix + raw.rstrip("\n"))
        stream.close()

    def start(self, app_id: int, name: str, workdir: str, command: str, env: dict | None = None) -> dict:
        mp = self.get(app_id, name)
        if mp.process and mp.process.poll() is None:
            return {"ok": False, "message": f"应用 {name} 已在运行 (PID {mp.process.pid})"}
        if not command or not command.strip():
            return {"ok": False, "message": "未设置启动命令"}

        merged_env = os.environ.copy()
        if env:
            merged_env.update({str(k): str(v) for k, v in env.items()})
        use_shell = sys.platform == "win32"
        mp.process = subprocess.Popen(
            command,
            cwd=workdir if os.path.isdir(workdir) else None,
            shell=use_shell,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=merged_env,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if use_shell else 0,
        )
        mp.started_at = time.time()
        self._append(mp, f"[deployhub] started: {command}")
        threading.Thread(target=self._pump, args=(mp, mp.process.stdout), daemon=True).start()
        return {"ok": True, "message": f"应用 {name} 已启动", "pid": mp.process.pid}

    def stop(self, app_id: int, name: str, force: bool = False) -> dict:
        mp = self.get(app_id, name)
        proc = mp.process
        if proc is None or proc.poll() is not None:
            return {"ok": True, "message": f"应用 {name} 未在运行"}
        try:
            if sys.platform == "win32":
                import ctypes

                ctypes.windll.kernel32.GenerateConsoleCtrlEvent(1, proc.pid)
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True)
            else:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL if force else signal.SIGTERM)
            self._append(mp, "[deployhub] stopped")
        except Exception as exc:
            return {"ok": False, "message": f"停止失败: {exc}"}
        return {"ok": True, "message": f"应用 {name} 已停止"}

    def restart(self, app_id: int, name: str, workdir: str, command: str, env: dict | None = None) -> dict:
        self.stop(app_id, name, force=True)
        time.sleep(0.5)
        return self.start(app_id, name, workdir, command, env)

    def status(self, app_id: int, name: str = "") -> dict:
        return self.get(app_id, name).snapshot()

    def status_all(self) -> list[dict]:
        return [mp.snapshot() for mp in self._procs.values()]

    def logs(self, app_id: int, name: str, tail: int = 200) -> list[str]:
        mp = self.get(app_id, name)
        lines = list(mp.log_buffer)
        if not lines:
            path = self.log_file(name)
            if os.path.exists(path):
                with open(path, encoding="utf-8", errors="replace") as f:
                    lines = f.readlines()[-tail:]
        return [ln.rstrip("\n") for ln in lines[-tail:]]

    def clear_logs(self, app_id: int, name: str):
        mp = self.get(app_id, name)
        mp.log_buffer.clear()
        path = self.log_file(name)
        if os.path.exists(path):
            open(path, "w").close()


process_manager = ProcessManager()
