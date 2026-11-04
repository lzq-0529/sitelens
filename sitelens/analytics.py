from __future__ import annotations

import json
import math
import secrets
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.orm import Session

from .detect import classify_agent, device_of, source_of
from .models import Crawl, Event, Order, Visitor, utcnow
from .siteconfig import infer_region, load_site

FUNNEL_STEPS = (
    ("visit", "浏览网站", "pageview"),
    ("product", "看商品", "view_item"),
    ("cart", "加入购物车", "add_to_cart"),
    ("checkout", "开始结账", "begin_checkout"),
    ("order", "完成下单", "purchase"),
)

EVENT_FLAGS = {
    "view_item": "viewed_item",
    "add_to_cart": "added_cart",
    "begin_checkout": "began_checkout",
    "purchase": "ordered",
    "signup": "signed_up",
}

KIND_LABELS = {"human": "真人", "bot": "爬虫/机器人", "unknown": "未知"}


def new_visitor_id() -> str:
    return secrets.token_urlsafe(16)[:22]


def _as_utc(value: datetime | None) -> datetime:
    if value is None:
        return utcnow()
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


MAX_DAYS = 3660
MAX_PROPS_CHARS = 8000


def clamp_days(days: int | str | None, default: int = 28) -> int:
    try:
        if isinstance(days, float) and not math.isfinite(days):
            value = default
        else:
            value = int(days)
    except (TypeError, ValueError, OverflowError):
        value = default
    return max(1, min(MAX_DAYS, value))


def since(days: int) -> datetime:
    return utcnow() - timedelta(days=clamp_days(days))


def parse_http_status(raw: object, default: int = 200) -> int:
    if isinstance(raw, bool) or isinstance(raw, (list, dict, tuple, set)):
        return default
    if isinstance(raw, float) and not math.isfinite(raw):
        return default
    if isinstance(raw, str) and raw.strip().lower() in {"inf", "+inf", "-inf", "nan", "infinity", "+infinity", "-infinity"}:
        return default
    try:
        value = int(raw)
    except (TypeError, ValueError, OverflowError):
        return default
    return value if 0 <= value <= 999 else default


def contains_like(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def capped_props(props: dict[str, Any]) -> str:
    blob = json.dumps(props, ensure_ascii=False)
    if len(blob) > MAX_PROPS_CHARS:
        return json.dumps({"_truncated": True, "keys": list(props)[:20]}, ensure_ascii=False)
    return blob


def region_filter(column, region: str):
    if region in {"cn", "intl"}:
        return column == region
    return True


def extract_account(payload: dict[str, Any], props: dict[str, Any] | None = None) -> str:
    bags = [payload]
    if isinstance(props, dict):
        bags.append(props)
    elif isinstance(payload.get("props"), dict):
        bags.append(payload["props"])
    for bag in bags:
        for key in ("account", "email", "user_id", "userId", "customer_email", "customerEmail"):
            value = str(bag.get(key) or "").strip()
            if value:
                return value[:120]
    return ""


def ingest_event(db: Session, payload: dict[str, Any], *, ip: str = "", default_ua: str = "") -> Event:
    site = load_site(db)
    name = str(payload.get("name") or payload.get("event") or "pageview").strip()[:40] or "pageview"
    visitor_id = str(payload.get("visitor_id") or payload.get("vid") or "").strip() or new_visitor_id()
    host = str(payload.get("host") or payload.get("hostname") or "").strip()[:160]
    region = infer_region(site, host, str(payload.get("region") or ""))
    user_agent = str(payload.get("user_agent") or payload.get("ua") or default_ua or "")[:2000]
    kind, engine, _category = classify_agent(user_agent)
    referrer = str(payload.get("referrer") or payload.get("ref") or "")[:255]
    utm = str(payload.get("utm") or payload.get("source") or "")
    source = source_of(referrer, utm)
    props = payload.get("props") if isinstance(payload.get("props"), dict) else {}
    account = extract_account(payload, props)
    path = str(payload.get("path") or payload.get("url") or "/")[:512]
    title = str(payload.get("title") or "")[:255]
    stamp = payload.get("at")
    if isinstance(stamp, str):
        try:
            at = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        except ValueError:
            at = utcnow()
    else:
        at = utcnow()
    event = Event(
        at=_as_utc(at),
        name=name,
        visitor_id=visitor_id,
        region=region,
        path=path,
        title=title,
        referrer=referrer,
        source=source,
        host=host,
        ip=str(payload.get("ip") or ip or "")[:64],
        user_agent=user_agent,
        device=device_of(user_agent),
        kind=kind,
        account=account,
        props=capped_props(props),
    )
    db.add(event)
    _touch_visitor(db, event)
    if kind == "bot":
        db.add(
            Crawl(
                at=event.at,
                region=region,
                engine=engine.lower() or "bot",
                label=engine or "未知爬虫",
                ip=event.ip,
                path=path,
                status=parse_http_status(payload.get("status"), 200),
                user_agent=user_agent,
            )
        )
    if name == "purchase":
        _order_from_purchase(db, event, props, site)
    db.flush()
    return event


def ingest_crawl(db: Session, payload: dict[str, Any], *, ip: str = "") -> Crawl:
    site = load_site(db)
    user_agent = str(payload.get("user_agent") or payload.get("ua") or "")[:2000]
    kind, engine, _category = classify_agent(user_agent)
    host = str(payload.get("host") or "")[:160]
    row = Crawl(
        at=utcnow(),
        region=infer_region(site, host, str(payload.get("region") or "")),
        engine=str(payload.get("engine") or engine.lower() or "bot")[:32],
        label=str(payload.get("label") or engine or "未知爬虫")[:80],
        ip=str(payload.get("ip") or ip or "")[:64],
        path=str(payload.get("path") or "/")[:512],
        status=parse_http_status(payload.get("status"), 200),
        user_agent=user_agent,
        verified=str(payload.get("verified") or "unchecked")[:16],
    )
    if kind == "human" and not payload.get("engine"):
        row.engine = "unknown"
        row.label = "未识别"
    db.add(row)
    db.flush()
    return row


def _touch_visitor(db: Session, event: Event) -> Visitor:
    row = db.get(Visitor, event.visitor_id)
    if row is None:
        row = Visitor(
            id=event.visitor_id,
            first_at=event.at,
            last_at=event.at,
            region=event.region,
            kind=event.kind,
            ip=event.ip,
            device=event.device,
            referrer=event.referrer,
            source=event.source,
            account=event.account,
            user_agent=event.user_agent,
            views=0,
        )
        db.add(row)
    row.last_at = event.at
    row.region = event.region or row.region
    row.kind = event.kind or row.kind
    if event.ip:
        row.ip = event.ip
    if event.device:
        row.device = event.device
    if event.referrer and (not row.referrer or row.source == "直接访问"):
        row.referrer = event.referrer
        row.source = event.source
    if event.account:
        row.account = event.account
    if event.user_agent:
        row.user_agent = event.user_agent
    if event.name == "pageview":
        row.views = (row.views or 0) + 1
    flag = EVENT_FLAGS.get(event.name)
    if flag:
        setattr(row, flag, True)
    if row.views is None:
        row.views = 0
    return row


def _order_from_purchase(db: Session, event: Event, props: dict[str, Any], site: dict[str, Any]) -> Order | None:
    from .orders import coerce_amount_cents, create_order

    amount = coerce_amount_cents(props if isinstance(props, dict) else {})
    if amount is None:
        return None
    external = str(props.get("order_id") or props.get("id") or "").strip()
    if external:
        existing = db.scalar(select(Order).where(Order.id == external))
        if existing is not None:
            return existing
    return create_order(
        db,
        {
            "id": external,
            "sku": props.get("sku") or "",
            "title": props.get("title") or props.get("product") or "网站下单",
            "amount_cents": amount,
            "currency": props.get("currency") or site.get("currency") or "CNY",
            "channel": props.get("channel") or "独立站收银台",
            "customer": props.get("customer") or event.account,
            "region": event.region,
            "source": "tracker",
            "visitor_id": event.visitor_id,
            "at": event.at.isoformat(),
        },
    )


def _scope_filter(kind: str):
    if kind == "human":
        return Event.kind == "human"
    if kind == "bot":
        return Event.kind == "bot"
    return True


def _visitor_ids(db: Session, *, days: int, region: str, scope: str, name: str | None = None) -> set[str]:
    stmt = select(Event.visitor_id).where(Event.at >= since(days), _scope_filter(scope))
    if region in {"cn", "intl"}:
        stmt = stmt.where(Event.region == region)
    if name:
        stmt = stmt.where(Event.name == name)
    return {row[0] for row in db.execute(stmt.distinct()).all() if row[0]}


def _rank(counter: Counter[str], limit: int = 12) -> list[dict[str, Any]]:
    return [{"name": name or "—", "visitors": count} for name, count in counter.most_common(limit)]


def build_summary(db: Session, *, days: int = 28, scope: str = "human", region: str = "all") -> dict[str, Any]:
    days = clamp_days(days)
    start = since(days)
    stmt = select(Event).where(Event.at >= start, _scope_filter(scope))
    if region in {"cn", "intl"}:
        stmt = stmt.where(Event.region == region)
    events = list(db.scalars(stmt))
    by_region = {"cn": defaultdict(set), "intl": defaultdict(set)}
    daily: dict[str, dict[str, Any]] = {}
    sources: Counter[str] = Counter()
    devices: Counter[str] = Counter()
    landings: Counter[str] = Counter()
    pages: Counter[str] = Counter()
    visitor_flags: dict[str, set[str]] = defaultdict(set)
    kinds: Counter[str] = Counter()

    for event in events:
        day = _as_utc(event.at).strftime("%Y-%m-%d")
        slot = daily.setdefault(
            day,
            {
                "day": day,
                "visitors": set(),
                "views": 0,
                "product": set(),
                "cart": set(),
                "checkout": set(),
                "order": set(),
                "cn_visitors": set(),
                "intl_visitors": set(),
                "cn_views": 0,
                "intl_views": 0,
            },
        )
        kinds[event.kind] += 1
        visitor_flags[event.visitor_id].add(event.name)
        if event.name == "pageview":
            slot["views"] += 1
            slot["visitors"].add(event.visitor_id)
            slot[f"{event.region}_views"] = slot.get(f"{event.region}_views", 0) + 1
            slot[f"{event.region}_visitors"].add(event.visitor_id)
            by_region[event.region]["visit"].add(event.visitor_id)
            sources[event.source or "直接访问"] += 1
            devices[event.device or "未知设备"] += 1
            landings[event.path or "/"] += 1
            pages[event.path or "/"] += 1
        mapping = {"view_item": "product", "add_to_cart": "cart", "begin_checkout": "checkout", "purchase": "order"}
        key = mapping.get(event.name)
        if key:
            slot[key].add(event.visitor_id)
            by_region[event.region][key].add(event.visitor_id)

    series = []
    for day in sorted(daily):
        row = daily[day]
        series.append(
            {
                "day": day,
                "visitors": len(row["visitors"]),
                "views": row["views"],
                "product": len(row["product"]),
                "cart": len(row["cart"]),
                "checkout": len(row["checkout"]),
                "order": len(row["order"]),
                "cn_visitors": len(row["cn_visitors"]),
                "intl_visitors": len(row["intl_visitors"]),
                "cn_views": row["cn_views"],
                "intl_views": row["intl_views"],
            }
        )

    unique = {name: _visitor_ids(db, days=days, region=region, scope=scope, name=name) for _, _, name in FUNNEL_STEPS}
    funnel = []
    for step_id, label, name in FUNNEL_STEPS:
        ids = unique[name]
        funnel.append(
            {
                "id": step_id,
                "label": label,
                "count": len(ids),
                "cn_count": len(_visitor_ids(db, days=days, region="cn", scope=scope, name=name)),
                "intl_count": len(_visitor_ids(db, days=days, region="intl", scope=scope, name=name)),
            }
        )

    identified = db.scalar(
        select(func.count()).select_from(Visitor).where(Visitor.account != "", Visitor.last_at >= start)
    ) or 0
    return {
        "generated_at": utcnow().isoformat(),
        "since": start.isoformat(),
        "days": days,
        "scope": scope,
        "region": region,
        "site": {
            "visitors": len(unique["pageview"]),
            "views": sum(row["views"] for row in series),
            "product": len(unique["view_item"]),
            "cart": len(unique["add_to_cart"]),
            "checkout": len(unique["begin_checkout"]),
            "order": len(unique["purchase"]),
            "series": series,
            "referrers": _rank(sources),
            "source_breakdown": [{"name": name, "channel": name, "visitors": count} for name, count in sources.most_common(15)],
            "devices": _rank(devices),
            "landings": _rank(landings),
            "pages": _rank(pages),
        },
        "users": {
            "identified": identified,
            "signed_up": len(_visitor_ids(db, days=days, region=region, scope=scope, name="signup")),
        },
        "funnel": funnel,
        "kinds": dict(kinds),
        "kind_labels": KIND_LABELS,
        "regions": {
            "cn": {
                "site_visitors": len(by_region["cn"]["visit"]),
                "site_views": sum(row["cn_views"] for row in series),
                "product": len(by_region["cn"]["product"]),
                "cart": len(by_region["cn"]["cart"]),
                "order": len(by_region["cn"]["order"]),
            },
            "intl": {
                "site_visitors": len(by_region["intl"]["visit"]),
                "site_views": sum(row["intl_views"] for row in series),
                "product": len(by_region["intl"]["product"]),
                "cart": len(by_region["intl"]["cart"]),
                "order": len(by_region["intl"]["order"]),
            },
        },
    }


def build_search(db: Session, *, days: int = 28, region: str = "all") -> dict[str, Any]:
    days = clamp_days(days)
    start = since(days)
    stmt = select(Crawl).where(Crawl.at >= start)
    if region in {"cn", "intl"}:
        stmt = stmt.where(Crawl.region == region)
    rows = list(db.scalars(stmt))
    engines: dict[str, dict[str, Any]] = {}
    for row in rows:
        item = engines.setdefault(
            row.engine or row.label,
            {
                "id": row.engine or row.label,
                "label": row.label or row.engine,
                "hits": 0,
                "cn_hits": 0,
                "intl_hits": 0,
                "pages": set(),
                "verified": 0,
                "last": None,
            },
        )
        item["hits"] += 1
        item[f"{row.region}_hits"] = item.get(f"{row.region}_hits", 0) + 1
        item["pages"].add(row.path)
        if row.verified == "verified":
            item["verified"] += 1
        stamp = row.at.isoformat(timespec="minutes")
        if not item["last"] or stamp > item["last"]:
            item["last"] = stamp
    listed = []
    for item in engines.values():
        listed.append(
            {
                **item,
                "pages": sorted(item["pages"])[:20],
                "page_count": len(item["pages"]),
                "crawl": {
                    "hits": item["hits"],
                    "cn_hits": item.get("cn_hits", 0),
                    "intl_hits": item.get("intl_hits", 0),
                    "page_count": len(item["pages"]),
                    "verified": item["verified"],
                    "last": item["last"],
                    "pages": sorted(item["pages"])[:20],
                },
            }
        )
    listed.sort(key=lambda item: item["hits"], reverse=True)
    return {
        "generated_at": utcnow().isoformat(),
        "totals": {
            "hits": len(rows),
            "verified": sum(1 for row in rows if row.verified == "verified"),
            "cn_hits": sum(1 for row in rows if row.region == "cn"),
            "intl_hits": sum(1 for row in rows if row.region == "intl"),
        },
        "engines": listed,
    }


def mask_ip(ip: str) -> str:
    """Never hand a full visitor IP to the console: 203.0.113.42 -> 203.0.113.*"""
    text = str(ip or "").strip()
    if not text or "*" in text:
        return text
    if ":" in text:  # IPv6: keep the first three groups only
        parts = [part for part in text.split(":") if part]
        return ":".join(parts[:3]) + ":*" if len(parts) > 3 else text
    parts = text.split(".")
    if len(parts) == 4:
        return ".".join(parts[:3] + ["*"])
    return text


def visitor_view(row: Visitor) -> dict[str, Any]:
    return {
        "id": row.id,
        "first": row.first_at.strftime("%m-%d %H:%M") if row.first_at else "",
        "last": row.last_at.strftime("%m-%d %H:%M") if row.last_at else "",
        "first_at": row.first_at.isoformat() if row.first_at else None,
        "last_at": row.last_at.isoformat() if row.last_at else None,
        "region": row.region,
        "kind": row.kind,
        "kind_label": KIND_LABELS.get(row.kind, row.kind),
        "place": row.place,
        "ip": mask_ip(row.ip),
        "device": row.device,
        "referrer": row.referrer,
        "source": row.source,
        "account": row.account,
        "user_agent": row.user_agent,
        "site_views": row.views,
        "viewed_item": row.viewed_item,
        "added_cart": row.added_cart,
        "began_checkout": row.began_checkout,
        "ordered": row.ordered,
        "signed_up": row.signed_up,
        "note": row.note,
    }


def list_visitors(
    db: Session,
    *,
    days: int = 28,
    region: str = "all",
    scope: str = "human",
    q: str = "",
    behaviour: str = "",
    identified: bool = False,
    current: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    stmt = select(Visitor).where(Visitor.last_at >= since(days))
    if region in {"cn", "intl"}:
        stmt = stmt.where(Visitor.region == region)
    if scope in {"human", "bot"}:
        stmt = stmt.where(Visitor.kind == scope)
    if identified:
        stmt = stmt.where(Visitor.account != "")
    flags = {
        "product": Visitor.viewed_item.is_(True),
        "cart": Visitor.added_cart.is_(True),
        "checkout": Visitor.began_checkout.is_(True),
        "order": Visitor.ordered.is_(True),
        "signup": Visitor.signed_up.is_(True),
    }
    if behaviour in flags:
        stmt = stmt.where(flags[behaviour])
    if q:
        like = contains_like(q)
        stmt = stmt.where(
            or_(
                Visitor.ip.like(like, escape="\\"),
                Visitor.account.like(like, escape="\\"),
                Visitor.referrer.like(like, escape="\\"),
                Visitor.source.like(like, escape="\\"),
                Visitor.device.like(like, escape="\\"),
                Visitor.note.like(like, escape="\\"),
                Visitor.id.like(like, escape="\\"),
            )
        )
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    rows = list(
        db.scalars(stmt.order_by(desc(Visitor.last_at)).offset(max(0, (current - 1) * page_size)).limit(page_size))
    )
    return {"data": [visitor_view(row) for row in rows], "total": total, "success": True}


def list_events(
    db: Session,
    *,
    days: int = 28,
    region: str = "all",
    name: str = "",
    q: str = "",
    current: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    stmt = select(Event).where(Event.at >= since(days), Event.kind == "human")
    if region in {"cn", "intl"}:
        stmt = stmt.where(Event.region == region)
    if name:
        stmt = stmt.where(Event.name == name)
    if q:
        like = contains_like(q)
        stmt = stmt.where(
            or_(
                Event.path.like(like, escape="\\"),
                Event.account.like(like, escape="\\"),
                Event.source.like(like, escape="\\"),
                Event.ip.like(like, escape="\\"),
            )
        )
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    rows = list(db.scalars(stmt.order_by(desc(Event.at)).offset(max(0, (current - 1) * page_size)).limit(page_size)))
    return {
        "data": [
            {
                "id": row.id,
                "at": row.at.isoformat(),
                "name": row.name,
                "visitor_id": row.visitor_id,
                "region": row.region,
                "path": row.path,
                "title": row.title,
                "source": row.source,
                "account": row.account,
                "ip": mask_ip(row.ip),
                "device": row.device,
            }
            for row in rows
        ],
        "total": total,
        "success": True,
    }


def list_crawls(
    db: Session,
    *,
    days: int = 28,
    region: str = "all",
    q: str = "",
    current: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    stmt = select(Crawl).where(Crawl.at >= since(days))
    if region in {"cn", "intl"}:
        stmt = stmt.where(Crawl.region == region)
    if q:
        like = contains_like(q)
        stmt = stmt.where(
            or_(
                Crawl.engine.like(like, escape="\\"),
                Crawl.label.like(like, escape="\\"),
                Crawl.path.like(like, escape="\\"),
                Crawl.ip.like(like, escape="\\"),
            )
        )
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    rows = list(db.scalars(stmt.order_by(desc(Crawl.at)).offset(max(0, (current - 1) * page_size)).limit(page_size)))
    return {
        "data": [
            {
                "id": row.id,
                "time": row.at.strftime("%m-%d %H:%M"),
                "at": row.at.isoformat(),
                "region": row.region,
                "engine": row.engine,
                "label": row.label,
                "ip": mask_ip(row.ip),
                "path": row.path,
                "status": row.status,
                "verified": row.verified,
                "user_agent": row.user_agent,
            }
            for row in rows
        ],
        "total": total,
        "success": True,
    }


def users_summary(db: Session, *, region: str = "all") -> dict[str, Any]:
    stmt = select(Visitor).where(Visitor.kind == "human")
    if region in {"cn", "intl"}:
        stmt = stmt.where(Visitor.region == region)
    rows = list(db.scalars(stmt))
    return {
        "visitors": len(rows),
        "identified": sum(1 for row in rows if row.account),
        "signed_up": sum(1 for row in rows if row.signed_up),
        "ordered": sum(1 for row in rows if row.ordered),
        "cart": sum(1 for row in rows if row.added_cart),
        "cn": sum(1 for row in rows if row.region == "cn"),
        "intl": sum(1 for row in rows if row.region == "intl"),
    }
