from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Setting, utcnow

SITE_KEY = "site"

DEFAULT_SITE: dict[str, Any] = {
    "brand": "流明好物",
    "brand_aliases": ["Lumen Goods", "lumen.shop"],
    "category": "家居与生活方式",
    "domains": ["lumen.shop", "www.lumen.shop", "lumen.example"],
    "cn_hosts": ["lumen.shop", "www.lumen.shop"],
    "intl_hosts": ["intl.lumen.shop", "lumen.example"],
    "keywords": ["独立站", "家居好物", "跨境电商"],
    "competitors": [],
    "owned_urls": ["https://lumen.shop/"],
    "currency": "CNY",
    "cn_label": "国内站",
    "intl_label": "海外站",
    "geo_schedule": "weekly",
}


def _normalize(raw: dict[str, Any] | None) -> dict[str, Any]:
    data = {**DEFAULT_SITE, **(raw or {})}
    for key in ("brand_aliases", "domains", "cn_hosts", "intl_hosts", "keywords", "competitors", "owned_urls"):
        values = data.get(key) or []
        if isinstance(values, str):
            values = [line.strip() for line in values.replace(",", "\n").splitlines() if line.strip()]
        data[key] = [str(item).strip() for item in values if str(item).strip()]
    data["brand"] = str(data.get("brand") or DEFAULT_SITE["brand"]).strip()
    data["category"] = str(data.get("category") or DEFAULT_SITE["category"]).strip()
    data["currency"] = str(data.get("currency") or "CNY").strip().upper()[:8]
    data["geo_schedule"] = "daily" if str(data.get("geo_schedule") or "").lower() == "daily" else "weekly"
    return data


def load_site(db: Session) -> dict[str, Any]:
    row = db.scalar(select(Setting).where(Setting.key == SITE_KEY))
    if row is None:
        return _normalize(None)
    try:
        parsed = json.loads(row.value or "{}")
    except json.JSONDecodeError:
        parsed = {}
    return _normalize(parsed if isinstance(parsed, dict) else {})


def save_site(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    current = load_site(db)
    next_value = _normalize({**current, **(payload or {})})
    row = db.scalar(select(Setting).where(Setting.key == SITE_KEY))
    blob = json.dumps(next_value, ensure_ascii=False)
    if row is None:
        db.add(Setting(key=SITE_KEY, value=blob, updated_at=utcnow()))
    else:
        row.value = blob
        row.updated_at = utcnow()
    db.flush()
    return next_value


def infer_region(site: dict[str, Any], host: str, explicit: str = "") -> str:
    raw = str(explicit or "").strip().lower()
    if raw in {"cn", "china", "domestic"}:
        return "cn"
    if raw in {"intl", "global", "overseas", "international"}:
        return "intl"
    host = (host or "").split(":")[0].lower().removeprefix("www.")
    for item in site.get("intl_hosts") or []:
        if host and host == str(item).lower().removeprefix("www."):
            return "intl"
    return "cn"
