from __future__ import annotations

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from ..core.security import decode_token, require_role
from ..services.ports import list_listening_ports
from ..services.process_manager import process_manager

router = APIRouter(prefix="/api/ports", tags=["ports"])


@router.get("")
def listening_ports(user=Depends(require_role("viewer"))):
    items = list_listening_ports()
    # tag ports owned by managed apps (including their child processes)
    from ..services.ports import app_port_map
    from ..database import SessionLocal
    from ..models import App

    db = SessionLocal()
    try:
        apps = db.query(App).all()
        managed = [process_manager.status(a.id, a.name) for a in apps]
        port_map = app_port_map(managed)
    finally:
        db.close()
    for item in items:
        item["app"] = port_map.get(item["port"], "")
    return items


@router.websocket("/terminal")
async def terminal(ws: WebSocket):
    """Online shell over WebSocket: /api/ports/terminal?token=xxx  (operator+ only)."""
    token = ws.query_params.get("token", "")
    try:
        payload = decode_token(token)
    except Exception:
        await ws.close(code=4401)
        return
    if {"viewer": 1, "operator": 2, "admin": 3}.get(payload.get("role", ""), 0) < 2:
        await ws.close(code=4403)
        return

    import asyncio
    import os
    import sys

    await ws.accept()
    if sys.platform == "win32":
        import subprocess

        proc = subprocess.Popen(
            ["cmd.exe"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            shell=False, text=True, encoding="utf-8", errors="replace",
        )
        loop = asyncio.get_event_loop()

        async def reader():
            for line in iter(proc.stdout.readline, ""):
                if not line:
                    break
                try:
                    await ws.send_text(line)
                except Exception:
                    break

        read_task = loop.create_task(reader())
        try:
            while True:
                data = await ws.receive_text()
                proc.stdin.write(data + "\n")
                proc.stdin.flush()
        except WebSocketDisconnect:
            pass
        finally:
            read_task.cancel()
            proc.kill()
    else:
        import pty

        pid, fd = pty.fork()
        if pid == 0:
            os.execvp(os.environ.get("SHELL", "/bin/bash"), [os.environ.get("SHELL", "/bin/bash")])

        loop = asyncio.get_event_loop()

        async def reader():
            while True:
                try:
                    data = await loop.run_in_executor(None, os.read, fd, 4096)
                except OSError:
                    break
                if not data:
                    break
                try:
                    await ws.send_text(data.decode("utf-8", "replace"))
                except Exception:
                    break

        read_task = loop.create_task(reader())
        try:
            while True:
                data = await ws.receive_text()
                os.write(fd, data.encode())
        except WebSocketDisconnect:
            pass
        finally:
            read_task.cancel()
            try:
                os.kill(pid, 9)
            except OSError:
                pass
