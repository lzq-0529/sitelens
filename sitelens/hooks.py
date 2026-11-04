from __future__ import annotations

import base64
import hashlib
import hmac
import json
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from .models import Order
from .orders import create_order
from .siteconfig import infer_region, load_site


def _compare(secret: str, raw: bytes, provided: str) -> bool:
    if not secret or not provided:
        return False
    expected = base64.b64encode(hmac.new(secret.encode("utf-8"), raw, hashlib.sha256).digest())
    try:
        left = str(provided).strip().encode("ascii")
    except (UnicodeEncodeError, TypeError):
        return False
    if len(left) != len(expected):
        return False
    return hmac.compare_digest(expected, left)


def _first_item(raw: Any) -> dict[str, Any]:
    if isinstance(raw, list) and raw:
        first = raw[0]
        return first if isinstance(first, dict) else {}
    if isinstance(raw, dict):
        first = next(iter(raw.values()), None)
        return first if isinstance(first, dict) else {}
    return {}


def parse_shopify(payload: dict[str, Any]) -> dict[str, Any] | None:
    status = str(payload.get("financial_status") or payload.get("status") or "").lower()
    if status and status not in {"paid", "partially_refunded", "authorized"}:
        return None
    item = _first_item(payload.get("line_items"))
    return {
        "id": f"shopify-{payload.get('id') or payload.get('order_number')}",
        "amount": payload.get("total_price") or payload.get("current_total_price") or 0,
        "currency": payload.get("currency") or "USD",
        "title": item.get("title") or payload.get("name") or "Shopify 订单",
        "sku": item.get("sku") or "",
        "customer": payload.get("email") or payload.get("contact_email") or "",
        "channel": "Shopify",
        "source": "shopify",
        "at": payload.get("created_at") or payload.get("processed_at") or "",
        "region": payload.get("region") or "",
    }


def parse_woocommerce(payload: dict[str, Any]) -> dict[str, Any] | None:
    status = str(payload.get("status") or "").lower()
    if status and status not in {"processing", "completed", "paid"}:
        return None
    item = _first_item(payload.get("line_items"))
    billing = payload.get("billing") if isinstance(payload.get("billing"), dict) else {}
    return {
        "id": f"woo-{payload.get('id')}",
        "amount": payload.get("total") or 0,
        "currency": payload.get("currency") or "CNY",
        "title": item.get("name") or item.get("title") or "WooCommerce 订单",
        "sku": item.get("sku") or "",
        "customer": billing.get("email") or payload.get("customer") or "",
        "channel": "独立站收银台",
        "source": "woocommerce",
        "at": payload.get("date_created") or payload.get("date_paid") or "",
        "region": payload.get("region") or "",
    }


def parse_generic(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": payload.get("id") or payload.get("order_id") or "",
        "amount": payload.get("amount"),
        "amount_cents": payload.get("amount_cents"),
        "currency": payload.get("currency") or "",
        "title": payload.get("title") or payload.get("product") or "网站下单",
        "sku": payload.get("sku") or "",
        "customer": payload.get("customer") or payload.get("email") or "",
        "channel": payload.get("channel") or "独立站收银台",
        "source": "webhook",
        "at": payload.get("at") or payload.get("created_at") or "",
        "region": payload.get("region") or "",
        "visitor_id": payload.get("visitor_id") or "",
    }


def ingest_hook_order(db: Session, parsed: dict[str, Any] | None) -> Order | None:
    if not parsed:
        return None
    site = load_site(db)
    if not parsed.get("region"):
        parsed["region"] = infer_region(site, str(parsed.get("host") or ""), "")
    order_id = str(parsed.get("id") or "").strip()
    if order_id:
        existing = db.get(Order, order_id)
        if existing is not None:
            return existing
    return create_order(db, parsed)


def verify_shopify(secret: str, raw: bytes, header: str) -> None:
    if not _compare(secret, raw, header):
        raise HTTPException(status_code=401, detail="Shopify 签名无效")


def verify_woo(secret: str, raw: bytes, header: str) -> None:
    if not _compare(secret, raw, header):
        raise HTTPException(status_code=401, detail="WooCommerce 签名无效")


def read_json(raw: bytes) -> dict[str, Any]:
    try:
        data = json.loads(raw.decode("utf-8") or "{}")
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail="不是合法 JSON") from exc
    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail="订单 webhook 必须是对象")
    return data
