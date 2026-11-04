from __future__ import annotations

from pathlib import Path
from threading import Lock
from time import monotonic
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from . import config
from .alerts import tick
from .analytics import ingest_crawl, ingest_event, new_visitor_id
from .auth import client_ip
from . import db as db_module
from .db import get_db
from .geo import geo_prompts, geo_tasks, ingest_results
from .hooks import ingest_hook_order, parse_generic, parse_shopify, parse_woocommerce, read_json, verify_shopify, verify_woo
from .security import collect_secret, hook_secret, is_production
from .siteconfig import load_site

router = APIRouter()
_MAX_PER_WINDOW = 240
_WINDOW = 60
_calls: dict[str, list[float]] = {}
_lock = Lock()


def _limit(request: Request) -> None:
    key = client_ip(request)
    now = monotonic()
    with _lock:
        recent = [stamp for stamp in _calls.get(key, []) if now - stamp < _WINDOW]
        if len(recent) >= _MAX_PER_WINDOW:
            raise HTTPException(status_code=429, detail="请求过于频繁")
        recent.append(now)
        _calls[key] = recent


def _verify_geo_token(request: Request, token: str = Query("")) -> None:
    expected = config.geo_token()
    provided = (
        token
        or request.headers.get("x-geo-token", "").strip()
        or request.headers.get("authorization", "").removeprefix("Bearer ").strip()
    )
    if not provided or provided != expected:
        raise HTTPException(status_code=401, detail="无效的 GEO 写入密钥（请携带 X-Geo-Token 或 Authorization: Bearer <token>）")


def _verify_collect_token(request: Request, db: Session) -> None:
    expected = collect_secret(db)
    provided = request.headers.get("x-sitelens-token", "").strip() or request.query_params.get("token", "")
    if not expected:
        if is_production():
            raise HTTPException(status_code=401, detail="生产环境必须配置采集密钥（SITELENS_COLLECT_TOKEN 或设置页 collect_token）")
        return
    if provided != expected:
        raise HTTPException(status_code=401, detail="无效的采集密钥")


def _verify_hook_token(request: Request, db: Session) -> None:
    expected = hook_secret(db)
    provided = request.headers.get("x-sitelens-token", "").strip() or request.headers.get("authorization", "").removeprefix("Bearer ").strip()
    if not expected or provided != expected:
        raise HTTPException(status_code=401, detail="无效的订单 webhook 密钥")


def _verify_cron_token(request: Request) -> None:
    expected = config.cron_token()
    provided = (
        request.headers.get("x-cron-token", "").strip()
        or request.headers.get("x-sitelens-token", "").strip()
        or request.query_params.get("token", "")
    )
    if not provided or provided != expected:
        raise HTTPException(status_code=401, detail="无效的定时任务密钥")


@router.get("/api/health")
def health() -> dict[str, str]:
    return {"ok": "sitelens"}


@router.get("/robots.txt", response_class=PlainTextResponse)
def robots() -> str:
    return "User-agent: *\nDisallow: /\n"


@router.get("/tracker.js", response_class=PlainTextResponse)
def tracker_js() -> str:
    return (Path(__file__).resolve().parent / "static" / "tracker.js").read_text(encoding="utf-8")


@router.post("/api/collect", dependencies=[Depends(_limit)])
def collect(payload: dict[str, Any] | list[dict[str, Any]], request: Request, db: Session = Depends(get_db)):
    _verify_collect_token(request, db)
    items = payload if isinstance(payload, list) else [payload]
    visitor = request.cookies.get("sl_vid") or new_visitor_id()
    stored = []
    for item in items[:40]:
        if not isinstance(item, dict):
            continue
        item.setdefault("visitor_id", visitor)
        event = ingest_event(db, item, ip=client_ip(request), default_ua=request.headers.get("user-agent", ""))
        visitor = event.visitor_id
        stored.append(event.id)
    db.commit()
    return {"ok": True, "accepted": len(stored), "visitor_id": visitor}


@router.post("/api/collect/crawl", dependencies=[Depends(_limit)])
def collect_crawl(payload: dict[str, Any], request: Request, db: Session = Depends(get_db)):
    _verify_collect_token(request, db)
    row = ingest_crawl(db, payload, ip=client_ip(request))
    db.commit()
    return {"ok": True, "id": row.id}


@router.get("/api/geo/tasks", dependencies=[Depends(_limit)])
def public_geo_tasks(request: Request, token: str = Query(""), db: Session = Depends(get_db)):
    _verify_geo_token(request, token)
    return geo_tasks(db)


@router.post("/api/geo/ingest", dependencies=[Depends(_limit)])
def public_geo_ingest(payload: dict[str, Any], request: Request, token: str = Query(""), db: Session = Depends(get_db)):
    _verify_geo_token(request, token)
    try:
        result = ingest_results(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    return result


@router.get("/api/geo/prompts", dependencies=[Depends(_limit)])
def public_geo_prompts(request: Request, token: str = Query(""), db: Session = Depends(get_db)):
    _verify_geo_token(request, token)
    return geo_prompts(db)


@router.post("/api/hooks/order", dependencies=[Depends(_limit)])
def hook_order(payload: dict[str, Any], request: Request, db: Session = Depends(get_db)):
    _verify_hook_token(request, db)
    row = ingest_hook_order(db, parse_generic(payload))
    db.commit()
    return {"ok": True, "id": row.id if row else None}


@router.post("/api/hooks/shopify", dependencies=[Depends(_limit)])
async def hook_shopify(request: Request):
    raw = await request.body()
    with db_module.SessionLocal() as db:
        site = load_site(db)
        verify_shopify(str(site.get("shopify_secret") or ""), raw, request.headers.get("x-shopify-hmac-sha256", ""))
        row = ingest_hook_order(db, parse_shopify(read_json(raw)))
        db.commit()
        return {"ok": True, "id": row.id if row else None, "skipped": row is None}


@router.post("/api/hooks/woocommerce", dependencies=[Depends(_limit)])
async def hook_woocommerce(request: Request):
    raw = await request.body()
    with db_module.SessionLocal() as db:
        site = load_site(db)
        verify_woo(str(site.get("woo_secret") or ""), raw, request.headers.get("x-wc-webhook-signature", ""))
        row = ingest_hook_order(db, parse_woocommerce(read_json(raw)))
        db.commit()
        return {"ok": True, "id": row.id if row else None, "skipped": row is None}


@router.post("/api/cron/tick")
def cron_tick(request: Request, db: Session = Depends(get_db)):
    _verify_cron_token(request)
    result = tick(db, force=bool(request.query_params.get("force")))
    db.commit()
    return result
