from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy import desc, func, or_, select
from sqlalchemy.orm import Session

from . import config
from .analytics import (
    MAX_DAYS,
    build_search,
    build_summary,
    clamp_days,
    contains_like,
    list_crawls,
    list_events,
    list_visitors,
    users_summary,
)
from .auth import (
    OWNER,
    audit,
    check_login_allowed,
    create_user,
    current_user,
    end_session,
    owner_user,
    record_login_failure,
    start_session,
    user_view,
    verify_password,
)
from .db import get_db
from .geo import geo_prompts, geo_report, ingest_results, save_geo_prompts
from .models import AuditLog, User
from .orders import create_order, list_orders, order_view, orders_summary, refund_order
from .security import public_settings
from .siteconfig import load_site, save_site

router = APIRouter(prefix="/api/admin")


def _page(current: int, page_size: int) -> tuple[int, int]:
    return max(1, current), min(100, max(1, page_size))


def _days(days: int, default: int = 28) -> int:
    return clamp_days(days, default)


@router.post("/login")
def login(payload: dict[str, Any], request: Request, response: Response, db: Session = Depends(get_db)):
    username = str(payload.get("username") or "").strip()
    password = str(payload.get("password") or "")
    check_login_allowed(request, username)
    user = db.scalar(select(User).where(User.username == username))
    if user is None or user.disabled or not verify_password(password, user.password_hash):
        record_login_failure(request, username)
        raise HTTPException(status_code=400, detail="用户名或密码不正确")
    start_session(db, user, response)
    audit(db, user, "login", user.username)
    db.commit()
    return user_view(user)


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db), user: User = Depends(current_user)):
    end_session(db, request, response)
    db.commit()
    return {"ok": True}


@router.get("/me")
def me(user: User = Depends(current_user)):
    return user_view(user)


@router.get("/overview")
def overview(
    days: int = Query(28, ge=1, le=MAX_DAYS),
    region: str = "all",
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
):
    days = _days(days)
    site = build_summary(db, days=days, region=region or "all")
    revenue = orders_summary(db, days=days)
    return {"site": site, "revenue": revenue, "users": users_summary(db, region=region or "all")}


@router.get("/site/summary")
def site_summary(
    days: int = Query(28, ge=1, le=MAX_DAYS),
    scope: str = "human",
    region: str = "all",
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
):
    return build_summary(db, days=_days(days), scope=scope, region=region)


@router.get("/site/search")
def site_search(
    days: int = Query(28, ge=1, le=MAX_DAYS),
    region: str = "all",
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
):
    return build_search(db, days=_days(days), region=region)


@router.get("/site/visitors")
def site_visitors(
    days: int = Query(28, ge=1, le=MAX_DAYS),
    scope: str = "human",
    region: str = "all",
    q: str = "",
    behaviour: str = "",
    identified: bool = False,
    current: int = 1,
    pageSize: int = 20,
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
):
    current, pageSize = _page(current, pageSize)
    return list_visitors(
        db,
        days=_days(days),
        region=region,
        scope=scope,
        q=q,
        behaviour=behaviour,
        identified=identified,
        current=current,
        page_size=pageSize,
    )


@router.get("/site/events")
def site_events(
    days: int = Query(28, ge=1, le=MAX_DAYS),
    region: str = "all",
    name: str = "",
    q: str = "",
    current: int = 1,
    pageSize: int = 20,
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
):
    current, pageSize = _page(current, pageSize)
    return list_events(db, days=_days(days), region=region, name=name, q=q, current=current, page_size=pageSize)


@router.get("/site/crawls")
def site_crawls(
    days: int = Query(28, ge=1, le=MAX_DAYS),
    region: str = "all",
    q: str = "",
    current: int = 1,
    pageSize: int = 20,
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
):
    current, pageSize = _page(current, pageSize)
    return list_crawls(db, days=_days(days), region=region, q=q, current=current, page_size=pageSize)


@router.get("/visitors/summary")
@router.get("/workbench/summary")
def visitors_summary(region: str = "all", db: Session = Depends(get_db), _: User = Depends(current_user)):
    return users_summary(db, region=region)


@router.get("/site/geo")
def site_geo(db: Session = Depends(get_db), user: User = Depends(current_user)):
    data = geo_report(db)
    if user.role == OWNER:
        data["ingest_token"] = config.geo_token()
    return data


@router.post("/site/geo/ingest")
def site_geo_ingest(payload: dict[str, Any], user: User = Depends(owner_user), db: Session = Depends(get_db)):
    try:
        result = ingest_results(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    audit(db, user, "geo_ingest", f"platforms={','.join(result.get('updated_platforms') or [])}")
    db.commit()
    return result


@router.get("/site/geo/prompts")
def get_prompts(db: Session = Depends(get_db), _: User = Depends(current_user)):
    return geo_prompts(db)


@router.post("/site/geo/prompts")
def post_prompts(payload: dict[str, Any], user: User = Depends(owner_user), db: Session = Depends(get_db)):
    try:
        prompts = save_geo_prompts(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    audit(db, user, "geo_prompts", f"cn={len(prompts.get('cn') or [])} intl={len(prompts.get('intl') or [])}")
    db.commit()
    return {"ok": True, "prompts": prompts}


@router.get("/orders/summary")
def admin_orders_summary(
    days: int = Query(30, ge=1, le=MAX_DAYS),
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
):
    return orders_summary(db, days=_days(days, 30))


@router.get("/orders")
def admin_list_orders(
    q: str = "",
    status: str = "",
    edition: str = "",
    region: str = "",
    start: str = "",
    end: str = "",
    current: int = 1,
    pageSize: int = 20,
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
):
    current, pageSize = _page(current, pageSize)
    return list_orders(db, q=q, status=status, region=region or edition, start=start, end=end, current=current, page_size=pageSize)


@router.post("/orders")
def admin_create_order(payload: dict[str, Any], user: User = Depends(owner_user), db: Session = Depends(get_db)):
    row = create_order(db, payload)
    audit(db, user, "create_order", f"{row.title} {row.amount_cents / 100:.2f} {row.customer}")
    db.commit()
    return order_view(row)


@router.post("/orders/{order_id}/refund")
def admin_refund(order_id: str, user: User = Depends(owner_user), db: Session = Depends(get_db)):
    row = refund_order(db, order_id)
    audit(db, user, "refund_order", f"{row.id} {row.amount_cents / 100:.2f}")
    db.commit()
    return order_view(row)


@router.get("/settings")
def get_settings(request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    data = public_settings(load_site(db), owner=user.role == OWNER)
    if user.role == OWNER:
        origin = str(request.base_url).rstrip("/")
        data = {
            **data,
            "ingest_token": config.geo_token(),
            "cron_token": config.cron_token(),
            "hooks": {
                "order": f"{origin}/api/hooks/order",
                "shopify": f"{origin}/api/hooks/shopify",
                "woocommerce": f"{origin}/api/hooks/woocommerce",
                "cron": f"{origin}/api/cron/tick",
            },
        }
    return data


@router.put("/settings")
def put_settings(payload: dict[str, Any], user: User = Depends(owner_user), db: Session = Depends(get_db)):
    data = public_settings(save_site(db, payload), owner=True)
    audit(db, user, "update_settings", data.get("brand") or "")
    db.commit()
    return data


@router.get("/users")
def list_users(
    q: str = "",
    current: int = 1,
    pageSize: int = 20,
    db: Session = Depends(get_db),
    _: User = Depends(owner_user),
):
    current, pageSize = _page(current, pageSize)
    stmt = select(User)
    if q:
        like = contains_like(q)
        stmt = stmt.where(or_(User.username.like(like, escape="\\"), User.display_name.like(like, escape="\\")))
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    rows = list(db.scalars(stmt.order_by(User.created_at).offset((current - 1) * pageSize).limit(pageSize)))
    return {"data": [user_view(row) for row in rows], "total": total, "success": True}


@router.post("/users")
def add_user(payload: dict[str, Any], user: User = Depends(owner_user), db: Session = Depends(get_db)):
    created = create_user(
        db,
        str(payload.get("username") or ""),
        str(payload.get("password") or ""),
        role=str(payload.get("role") or "viewer"),
        display_name=str(payload.get("display_name") or ""),
    )
    audit(db, user, "create_user", created.username)
    db.commit()
    return user_view(created)


@router.patch("/users/{user_id}")
def edit_user(user_id: str, payload: dict[str, Any], user: User = Depends(owner_user), db: Session = Depends(get_db)):
    from .auth import check_password_strength, hash_password

    row = db.get(User, user_id)
    if row is None:
        raise HTTPException(status_code=404, detail="账号不存在")
    if "display_name" in payload:
        row.display_name = str(payload.get("display_name") or "")[:80]
    if "disabled" in payload:
        if row.id == user.id:
            raise HTTPException(status_code=400, detail="不能停用自己")
        row.disabled = bool(payload.get("disabled"))
    if payload.get("password"):
        check_password_strength(str(payload["password"]))
        row.password_hash = hash_password(str(payload["password"]))
    if payload.get("role") in {"owner", "viewer"} and row.id != user.id:
        row.role = payload["role"]
    audit(db, user, "edit_user", row.username)
    db.commit()
    return user_view(row)


@router.get("/audit")
def list_audit(
    q: str = "",
    current: int = 1,
    pageSize: int = 20,
    db: Session = Depends(get_db),
    _: User = Depends(owner_user),
):
    current, pageSize = _page(current, pageSize)
    stmt = select(AuditLog)
    if q:
        like = contains_like(q)
        stmt = stmt.where(or_(AuditLog.action.like(like, escape="\\"), AuditLog.detail.like(like, escape="\\")))
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    rows = list(db.scalars(stmt.order_by(desc(AuditLog.at)).offset((current - 1) * pageSize).limit(pageSize)))
    return {
        "data": [
            {"id": row.id, "at": row.at.isoformat(), "user_id": row.user_id, "action": row.action, "detail": row.detail}
            for row in rows
        ],
        "total": total,
        "success": True,
    }
