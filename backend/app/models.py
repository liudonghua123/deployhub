from __future__ import annotations

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text

from .database import Base
from .core.timeutil import utcnow


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    password_hash = Column(String(256), nullable=False)
    role = Column(String(16), default="viewer", nullable=False)  # admin / operator / viewer
    enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "role": self.role,
            "enabled": self.enabled,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
        }


class App(Base):
    __tablename__ = "apps"

    id = Column(Integer, primary_key=True)
    name = Column(String(64), unique=True, nullable=False, index=True)
    repo_url = Column(String(256), default="", nullable=False)
    branch = Column(String(64), default="main", nullable=False)
    deploy_dir = Column(String(256), default="", nullable=False)
    init_command = Column(String(512), default="", nullable=False)   # e.g. "npm install"
    start_command = Column(String(512), default="", nullable=False)  # e.g. "npm run start"
    env_json = Column(Text, default="{}", nullable=False)            # {"KEY": "VALUE"}
    auto_deploy = Column(Boolean, default=True, nullable=False)
    description = Column(String(256), default="", nullable=False)
    created_at = Column(DateTime, default=utcnow)

    def to_dict(self):
        import json

        return {
            "id": self.id,
            "name": self.name,
            "repo_url": self.repo_url,
            "branch": self.branch,
            "deploy_dir": self.deploy_dir or f"./workspaces/{self.name}",
            "init_command": self.init_command,
            "start_command": self.start_command,
            "env": json.loads(self.env_json or "{}"),
            "auto_deploy": self.auto_deploy,
            "description": self.description,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
        }


from sqlalchemy.orm import relationship


class Deployment(Base):
    __tablename__ = "deployments"

    id = Column(Integer, primary_key=True)
    app_id = Column(Integer, ForeignKey("apps.id", ondelete="CASCADE"), nullable=False, index=True)
    commit = Column(String(64), default="", nullable=False)
    commit_msg = Column(String(256), default="", nullable=False)
    status = Column(String(16), default="running", nullable=False)  # running / success / failed
    log = Column(Text, default="", nullable=False)
    created_at = Column(DateTime, default=utcnow)

    app = relationship("App", backref="deployments")

    def to_dict(self):
        return {
            "id": self.id,
            "app_id": self.app_id,
            "commit": self.commit,
            "commit_msg": self.commit_msg,
            "status": self.status,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
        }


class Setting(Base):
    __tablename__ = "settings"

    key = Column(String(64), primary_key=True)
    value = Column(Text, default="", nullable=False)
