from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from ..core.security import decode_token, require_role
from ..database import get_db
from ..models import App, User
from ..services.process_manager import process_manager

router = APIRouter(prefix="/api/logs", tags=["logs"])


@router.get("/{app_id}")
def get_logs(app_id: int, tail: int = 200, db: Session = Depends(get_db), user: User = Depends(require_role("viewer"))):
    app = db.get(App, app_id)
    if not app:
        raise HTTPException(status_code=404, detail="应用不存在")
    return {"app": app.name, "lines": process_manager.logs(app.id, app.name, tail)}


@router.delete("/{app_id}")
def clear_logs(app_id: int, db: Session = Depends(get_db), user: User = Depends(require_role("operator"))):
    app = db.get(App, app_id)
    if not app:
        raise HTTPException(status_code=404, detail="应用不存在")
    process_manager.clear_logs(app.id, app.name)
    return {"message": "日志已清空"}


@router.websocket("/ws/{app_id}")
async def log_stream(ws: WebSocket, app_id: int):
    # Authenticate via query param token: /api/logs/ws/1?token=xxx
    from ..database import SessionLocal

    token = ws.query_params.get("token", "")
    try:
        payload = decode_token(token)
    except HTTPException:
        await ws.close(code=4401)
        return
    db = SessionLocal()
    try:
        app = db.get(App, app_id)
        if not app:
            await ws.close(code=4404)
            return
        mp = process_manager.get(app.id, app.name)
        await ws.accept()
        # send backlog
        for line in list(mp.log_buffer)[-200:]:
            await ws.send_text(line)
        q = None
        import asyncio

        queue: asyncio.Queue = asyncio.Queue(maxsize=500)
        mp.listeners.add(queue)
        try:
            while True:
                try:
                    line = await asyncio.wait_for(queue.get(), timeout=15)
                    await ws.send_text(line)
                except asyncio.TimeoutError:
                    await ws.send_text("")  # heartbeat
        except WebSocketDisconnect:
            pass
        finally:
            mp.listeners.discard(queue)
    finally:
        db.close()
