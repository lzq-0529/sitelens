from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import desc, func, or_, select
from sqlalchemy.orm import Session

from .auth import new_id
from .models import Order, utcnow
from .siteconfig import load_site

CHANNELS = ("独立站收银台", "微信", "支付宝", "Stripe", "PayPal", "Shopify", "对公转账", "其他")


def _parse_at(raw: Any) -> datetime:
    if isinstance(raw, datetime):
        return raw if raw.tzinfo else raw.replace(tzinfo=timezone.utc)
    if isinstance(raw, str) and raw.strip():
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            pass
    return utcnow()


def money_view(cents: int, currency: str = "CNY") -> str:
    symbol = "¥" if currency.upper() in {"CNY", "RMB"} else "$" if currency.upper() == "USD" else f"{currency} "
    return f"{symbol}{(cents or 0) / 100:,.2f}"


def order_view(row: Order) -> dict[str, Any]:
    return {
        "id": row.id,
        "at": row.at.isoformat() if row.at else None,
        "sku": row.sku,
        "title": row.title,
        "region": row.region,
        "amount_cents": row.amount_cents,
        "currency": row.currency,
        "channel": row.channel,
        "customer": row.customer,
        "note": row.note,
        "source": row.source,
        "visitor_id": row.visitor_id,
        "status": row.status,
    }


def create_order(db: Session, payload: dict[str, Any]) -> Order:
    amount = payload.get("amount_cents")
    if amount is None:
        try:
            amount = int(round(float(payload.get("amount") or 0) * 100))
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail="金额无效") from exc
    amount = int(amount)
    if amount <= 0:
        raise HTTPException(status_code=400, detail="订单金额必须大于 0")
    site = load_site(db)
    row = Order(
        id=str(payload.get("id") or new_id()),
        at=_parse_at(payload.get("at")),
        sku=str(payload.get("sku") or "")[:80],
        title=str(payload.get("title") or payload.get("product") or "独立站订单")[:160],
        region="intl" if str(payload.get("region") or payload.get("edition") or "cn") in {"intl", "global"} else "cn",
        amount_cents=amount,
        currency=str(payload.get("currency") or site.get("currency") or "CNY")[:8],
        channel=str(payload.get("channel") or "独立站收银台")[:32],
        customer=str(payload.get("customer") or "")[:120],
        note=str(payload.get("note") or "")[:255],
        source=str(payload.get("source") or "manual")[:16],
        visitor_id=str(payload.get("visitor_id") or "")[:40],
        status="paid",
    )
    db.add(row)
    db.flush()
    return row


def refund_order(db: Session, order_id: str) -> Order:
    row = db.get(Order, order_id)
    if row is None:
        raise HTTPException(status_code=404, detail="订单不存在")
    if row.status == "refunded":
        return row
    row.status = "refunded"
    db.flush()
    return row


def list_orders(
    db: Session,
    *,
    q: str = "",
    status: str = "",
    region: str = "",
    start: str = "",
    end: str = "",
    current: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    stmt = select(Order)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Order.customer.like(like), Order.channel.like(like), Order.sku.like(like), Order.title.like(like), Order.note.like(like)))
    if status:
        stmt = stmt.where(Order.status == status)
    if region in {"cn", "intl"}:
        stmt = stmt.where(Order.region == region)
    if start:
        stmt = stmt.where(Order.at >= datetime.fromisoformat(start))
    if end:
        stmt = stmt.where(Order.at <= datetime.fromisoformat(end + "T23:59:59") if len(end) == 10 else datetime.fromisoformat(end))
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    rows = list(db.scalars(stmt.order_by(desc(Order.at)).offset(max(0, (current - 1) * page_size)).limit(page_size)))
    return {"data": [order_view(row) for row in rows], "total": total, "success": True}


def _aware(value: datetime | None) -> datetime:
    if value is None:
        return utcnow()
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def orders_summary(db: Session, *, days: int = 30) -> dict[str, Any]:
    from .analytics import since

    start = since(days)
    rows = list(db.scalars(select(Order)))
    paid = [row for row in rows if row.status == "paid"]
    recent = [row for row in paid if _aware(row.at) >= start]
    month_start = utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month = [row for row in paid if _aware(row.at) >= month_start]
    daily: dict[str, int] = {}
    by_sku: dict[str, int] = {}
    for row in recent:
        day = _aware(row.at).strftime("%Y-%m-%d")
        daily[day] = daily.get(day, 0) + row.amount_cents
        label = row.title or row.sku or "未命名商品"
        by_sku[label] = by_sku.get(label, 0) + row.amount_cents
    return {
        "month_cents": sum(row.amount_cents for row in month),
        "d30_cents": sum(row.amount_cents for row in recent),
        "total_cents": sum(row.amount_cents for row in paid),
        "orders_d30": len(recent),
        "daily": [{"day": day, "cents": daily[day]} for day in sorted(daily)],
        "by_plan": [{"label": name, "cents": cents} for name, cents in sorted(by_sku.items(), key=lambda item: item[1], reverse=True)],
    }
