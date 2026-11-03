from __future__ import annotations

import os
import secrets
from pathlib import Path

SESSION_COOKIE = "sitelens_session"
SESSION_DAYS = 14


def data_dir() -> Path:
    path = Path(os.environ.get("SITELENS_DATA_DIR") or Path.home() / ".local" / "share" / "sitelens").expanduser()
    path.mkdir(parents=True, exist_ok=True)
    return path


def database_url() -> str:
    return os.environ.get("SITELENS_DATABASE_URL") or f"sqlite:///{data_dir() / 'sitelens.db'}"


def secret() -> str:
    configured = str(os.environ.get("SITELENS_SECRET_KEY") or "").strip()
    if configured:
        return configured
    path = data_dir() / "secret"
    if not path.is_file():
        path.write_text(secrets.token_urlsafe(32), encoding="utf-8")
        path.chmod(0o600)
    return path.read_text(encoding="utf-8").strip()


def cookie_secure() -> bool:
    return str(os.environ.get("SITELENS_COOKIE_SECURE") or "").strip().lower() in {"1", "true", "yes"}


def geo_token() -> str:
    """Bearer / X-Geo-Token for Grok, Muse, or any weekly GEO agent."""
    configured = str(os.environ.get("SITELENS_GEO_TOKEN") or "").strip()
    if configured:
        return configured
    path = data_dir() / "geo_token"
    if not path.is_file():
        path.write_text("slgeo_" + secrets.token_urlsafe(24), encoding="utf-8")
        path.chmod(0o600)
    return path.read_text(encoding="utf-8").strip()


def collect_token() -> str:
    """Optional shared secret for the public tracker. Empty means open collect."""
    return str(os.environ.get("SITELENS_COLLECT_TOKEN") or "").strip()
