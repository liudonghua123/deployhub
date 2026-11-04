from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import settings
from .database import Base, SessionLocal, engine
from .models import User
from .core.security import hash_password
from .routers import apps, auth, deploy, functions, logs, nginx, ports, users


def init_db():
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.username == "admin").first():
            db.add(User(username="admin", password_hash=hash_password("admin123"), role="admin"))
            db.add(User(username="operator", password_hash=hash_password("operator123"), role="operator"))
            db.add(User(username="viewer", password_hash=hash_password("viewer123"), role="viewer"))
            db.commit()
    finally:
        db.close()


def create_app() -> FastAPI:
    app = FastAPI(title=settings.APP_NAME, version="1.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(auth.router)
    app.include_router(apps.router)
    app.include_router(deploy.router)
    app.include_router(logs.router)
    app.include_router(ports.router)
    app.include_router(nginx.router)
    app.include_router(users.router)
    app.include_router(functions.router)

    @app.on_event("startup")
    def _startup():
        init_db()

    @app.get("/api/health")
    def health():
        return {"status": "ok", "app": settings.APP_NAME}

    return app


app = create_app()
