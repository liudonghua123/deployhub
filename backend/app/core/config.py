from __future__ import annotations

import os
from datetime import timedelta

from pydantic import BaseModel


class Settings(BaseModel):
    APP_NAME: str = "DeployHub"
    SECRET_KEY: str = os.getenv("DEPLOYHUB_SECRET", "change-me-in-production-0f3a9c")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 12
    DATABASE_URL: str = os.getenv("DEPLOYHUB_DB", "sqlite:///./deployhub.db")
    WORKSPACES_DIR: str = os.getenv("DEPLOYHUB_WORKSPACES", "./workspaces")
    LOGS_DIR: str = os.getenv("DEPLOYHUB_LOGS", "./logs")
    NGINX_CONF_DIR: str = os.getenv("DEPLOYHUB_NGINX_CONF", "/etc/nginx/conf.d")
    NGINX_BIN: str = os.getenv("DEPLOYHUB_NGINX_BIN", "nginx")
    GITHUB_WEBHOOK_SECRET: str = os.getenv("DEPLOYHUB_GITHUB_SECRET", "")

    @property
    def access_token_ttl(self) -> timedelta:
        return timedelta(minutes=self.ACCESS_TOKEN_EXPIRE_MINUTES)


settings = Settings()
