from __future__ import annotations

import os
from typing import Any

from sqlalchemy.orm import Session

from . import config
from .siteconfig import load_site

LOCAL_ORIGINS = (
    "http://127.0.0.1:8788",
    "http://localhost:8788",
    "http://127.0.0.1:5188",
    "http://localhost:5188",
)


def is_production() -> bool:
    return str(os.environ.get("SITELENS_ENV") or "").strip().lower() in {"prod", "production"}


def collect_secret(db: Session | None = None) -> str:
    env = config.collect_token()
    if env:
        return env
    if db is None:
        return ""
    return str(load_site(db).get("collect_token") or "").strip()


def hook_secret(db: Session) -> str:
    site = load_site(db)
    return str(site.get("hook_token") or "").strip() or collect_secret(db)


def cors_origins(db: Session | None = None) -> set[str]:
    origins = {item.strip().rstrip("/") for item in config.cors_origins() if item.strip()}
    origins.update(LOCAL_ORIGINS)
    if db is not None:
        site = load_site(db)
        for key in ("domains", "cn_hosts", "intl_hosts"):
            for raw in site.get(key) or []:
                host = str(raw).strip().removeprefix("https://").removeprefix("http://").split("/")[0]
                if host:
                    origins.add(f"https://{host}")
                    origins.add(f"http://{host}")
    return origins


def origin_allowed(origin: str, db: Session | None = None) -> bool:
    if not origin:
        return False
    return origin.rstrip("/") in cors_origins(db)


def cors_headers(origin: str) -> dict[str, str]:
    return {
        "access-control-allow-origin": origin,
        "access-control-allow-methods": "GET, POST, OPTIONS",
        "access-control-allow-headers": "content-type, x-sitelens-token, x-geo-token, authorization, x-shopify-hmac-sha256, x-wc-webhook-signature",
        "access-control-max-age": "600",
        "vary": "Origin",
    }


def public_settings(site: dict[str, Any], *, owner: bool) -> dict[str, Any]:
    data = dict(site)
    if not owner:
        for key in ("collect_token", "hook_token", "shopify_secret", "woo_secret", "alert_webhook", "cron_token"):
            data.pop(key, None)
    return data
