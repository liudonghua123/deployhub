from __future__ import annotations

from datetime import datetime, timezone


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def now_str() -> str:
    return utcnow().strftime("%Y-%m-%d %H:%M:%S")
