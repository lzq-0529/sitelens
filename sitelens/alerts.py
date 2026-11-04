from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import datetime
from typing import Any, Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Setting, utcnow
from .siteconfig import load_site, save_site

STATE_KEY = "alert_state"
Poster = Callable[[str, dict[str, Any]], None]


def _state(db: Session) -> dict[str, Any]:
    row = db.scalar(select(Setting).where(Setting.key == STATE_KEY))
    if row is None:
        return {}
    try:
        parsed = json.loads(row.value or "{}")
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _save_state(db: Session, payload: dict[str, Any]) -> None:
    row = db.scalar(select(Setting).where(Setting.key == STATE_KEY))
    blob = json.dumps(payload, ensure_ascii=False)
    if row is None:
        db.add(Setting(key=STATE_KEY, value=blob, updated_at=utcnow()))
    else:
        row.value = blob
        row.updated_at = utcnow()
    db.flush()


def build_snapshot(db: Session) -> dict[str, Any]:
    from .analytics import build_summary
    from .geo import geo_report
    from .orders import orders_summary

    site = load_site(db)
    summary = build_summary(db, days=1, region="all")
    revenue = orders_summary(db, days=1)
    geo = geo_report(db)
    due = sum(1 for item in geo.get("platforms") or [] if item.get("is_due"))
    cited = (geo.get("summary") or {}).get("owned_cited_count") or 0
    return {
        "type": "sitelens.daily",
        "brand": site.get("brand") or "",
        "window_hours": 24,
        "visitors": (summary.get("site") or {}).get("visitors") or 0,
        "orders": revenue.get("orders_d30") or 0,
        "revenue_cents": revenue.get("d30_cents") or 0,
        "geo_due": due,
        "geo_cited": cited,
        "at": utcnow().isoformat(),
    }


def post_json(url: str, payload: dict[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=body, method="POST", headers={"content-type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            response.read()
    except urllib.error.URLError as exc:
        raise RuntimeError(f"告警 webhook 发送失败：{exc}") from exc


def tick(db: Session, *, now: datetime | None = None, poster: Poster | None = None, force: bool = False) -> dict[str, Any]:
    site = load_site(db)
    url = str(site.get("alert_webhook") or "").strip()
    if not url:
        return {"sent": False, "reason": "no_webhook"}
    stamp = now or utcnow()
    if stamp.tzinfo is None:
        from datetime import timezone

        stamp = stamp.replace(tzinfo=timezone.utc)
    hour = int(site.get("alert_hour") or 0)
    if not force and stamp.hour < hour:
        return {"sent": False, "reason": "too_early"}
    day = stamp.strftime("%Y-%m-%d")
    state = _state(db)
    if not force and state.get("last_day") == day:
        return {"sent": False, "reason": "already"}
    payload = build_snapshot(db)
    (poster or post_json)(url, payload)
    _save_state(db, {"last_day": day, "last_at": stamp.isoformat()})
    return {"sent": True, "payload": payload}


def ensure_alert_fields(payload: dict[str, Any]) -> dict[str, Any]:
    current = dict(payload)
    current.setdefault("alert_webhook", "")
    current.setdefault("alert_hour", 1)
    return current


def save_alert_settings(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    return save_site(db, ensure_alert_fields(payload))
