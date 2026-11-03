from __future__ import annotations

from pathlib import Path
from threading import Lock
from time import monotonic
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from . import config
from .analytics import ingest_crawl, ingest_event, new_visitor_id
from .auth import client_ip
from .db import get_db
from .geo import geo_prompts, geo_tasks, ingest_results

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


def _verify_collect_token(request: Request) -> None:
    expected = config.collect_token()
    if not expected:
        return
    provided = request.headers.get("x-sitelens-token", "").strip() or request.query_params.get("token", "")
    if provided != expected:
        raise HTTPException(status_code=401, detail="无效的采集密钥")


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
    _verify_collect_token(request)
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
    _verify_collect_token(request)
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
