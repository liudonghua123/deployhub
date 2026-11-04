from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..core.security import require_role
from ..services.nginx_service import nginx_service

router = APIRouter(prefix="/api/nginx", tags=["nginx"])


@router.get("/configs")
def list_configs(user=Depends(require_role("viewer"))):
    return nginx_service.list_configs()


@router.get("/configs/{name}")
def read_config(name: str, user=Depends(require_role("viewer"))):
    try:
        return {"name": name, "content": nginx_service.read_config(name)}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


class ConfigBody(BaseModel):
    content: str


@router.put("/configs/{name}")
def write_config(name: str, body: ConfigBody, user=Depends(require_role("operator"))):
    return nginx_service.write_config(name, body.content)


@router.delete("/configs/{name}")
def delete_config(name: str, user=Depends(require_role("admin"))):
    try:
        return nginx_service.delete_config(name)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/test")
def test_config(user=Depends(require_role("operator"))):
    return nginx_service.test()


@router.post("/reload")
def reload_nginx(user=Depends(require_role("operator"))):
    return nginx_service.reload()


@router.post("/restart")
def restart_nginx(user=Depends(require_role("admin"))):
    return nginx_service.restart()
