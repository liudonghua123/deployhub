"""Nginx service: list/read/write site configs, test config, reload/restart."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys

from ..core.config import settings


class NginxService:
    def _run(self, *args: str) -> tuple[int, str]:
        try:
            proc = subprocess.run(
                [settings.NGINX_BIN, *args],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15,
            )
            out = (proc.stdout or "") + (proc.stderr or "")
            return proc.returncode, out.strip()
        except FileNotFoundError:
            return 127, "找不到 nginx 可执行文件，请通过环境变量 DEPLOYHUB_NGINX_BIN 指定路径"
        except subprocess.TimeoutExpired:
            return 124, "命令执行超时"

    def conf_dir(self) -> str:
        return settings.NGINX_CONF_DIR

    def list_configs(self) -> list[dict]:
        conf_dir = self.conf_dir()
        items = []
        if os.path.isdir(conf_dir):
            for fn in sorted(os.listdir(conf_dir)):
                if fn.endswith(".conf"):
                    path = os.path.join(conf_dir, fn)
                    try:
                        stat = os.stat(path)
                        items.append({
                            "name": fn,
                            "size": stat.st_size,
                            "modified": stat.st_mtime,
                        })
                    except OSError:
                        continue
        return items

    def read_config(self, name: str) -> str:
        safe = os.path.basename(name)
        path = os.path.join(self.conf_dir(), safe)
        if not os.path.isfile(path):
            raise FileNotFoundError(f"配置文件不存在: {safe}")
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()

    def write_config(self, name: str, content: str) -> dict:
        safe = os.path.basename(name)
        if not safe.endswith(".conf"):
            safe += ".conf"
        path = os.path.join(self.conf_dir(), safe)
        os.makedirs(self.conf_dir(), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return {"name": safe, "message": f"已保存 {safe}"}

    def delete_config(self, name: str) -> dict:
        safe = os.path.basename(name)
        path = os.path.join(self.conf_dir(), safe)
        if os.path.isfile(path):
            os.remove(path)
            return {"message": f"已删除 {safe}"}
        raise FileNotFoundError(f"配置文件不存在: {safe}")

    def test(self) -> dict:
        code, out = self._run("-t")
        return {"ok": code == 0, "output": out or "配置检查通过"}

    def reload(self) -> dict:
        code, out = self._run("-s", "reload")
        return {"ok": code == 0, "output": out or "nginx 已平滑重载"}

    def restart(self) -> dict:
        if sys.platform == "win32":
            # On Windows, stop then start via nginx.exe in its prefix dir
            code1, out1 = self._run("-s", "stop")
            code, out = self._run()
            ok = code == 0
            return {"ok": ok, "output": (out or "nginx 已重启") + (f" (stop: {out1})" if out1 and not ok else "")}
        if shutil.which("systemctl"):
            proc = subprocess.run(["systemctl", "restart", "nginx"], capture_output=True, text=True, timeout=15)
            return {"ok": proc.returncode == 0, "output": (proc.stdout + proc.stderr).strip() or "nginx 已重启"}
        code, out = self._run("-s", "quit")
        code2, out2 = self._run()
        return {"ok": code2 == 0, "output": (out2 or "nginx 已重启")}


nginx_service = NginxService()
