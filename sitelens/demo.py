from __future__ import annotations

import random
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from .analytics import ingest_crawl, ingest_event
from .auth import OWNER, create_user
from .geo import ingest_results
from .models import Event, User, utcnow
from .orders import create_order
from .siteconfig import save_site

SOURCES = ("直接访问", "Google", "百度", "小红书", "知乎", "Instagram", "Pinterest")
PATHS = ("/", "/products/wool-throw", "/products/pour-over", "/collections/home", "/cart", "/checkout")
SKUS = (
    ("wool-throw", "北岛羊毛毯", 29900),
    ("pour-over", "手冲咖啡套装", 18900),
    ("linen-set", "亚麻床品四件套", 45900),
)


def seed_demo(db: Session, *, owner_username: str = "owner", owner_password: str = "sitelens-demo") -> dict:
    if db.scalar(select(User).where(User.username == owner_username)) is None:
        create_user(db, owner_username, owner_password, role=OWNER, display_name="站点管理员")
    save_site(
        db,
        {
            "brand": "流明好物",
            "brand_aliases": ["Lumen Goods", "lumen.shop"],
            "category": "家居与生活方式",
            "domains": ["lumen.shop", "www.lumen.shop"],
            "competitors": ["示例竞品"],
        },
    )
    if db.scalar(select(Event.id)) is not None:
        return {"ok": True, "seeded": False, "message": "已有事件数据，跳过演示填充"}

    rng = random.Random(42)
    now = utcnow()
    for day in range(28):
        stamp = now - timedelta(days=27 - day)
        visitors = 18 + (day % 7) * 3
        for index in range(visitors):
            region = "intl" if index % 5 == 0 else "cn"
            visitor = f"demo_{day}_{index}"
            source = SOURCES[index % len(SOURCES)]
            path = PATHS[index % len(PATHS)]
            ingest_event(
                db,
                {
                    "name": "pageview",
                    "visitor_id": visitor,
                    "region": region,
                    "path": path,
                    "referrer": source if source != "直接访问" else "",
                    "source": source,
                    "at": stamp.isoformat(),
                    "user_agent": "Mozilla/5.0 Demo",
                    "account": f"buyer{index}@example.com" if index % 9 == 0 else "",
                },
            )
            if index % 3 == 0:
                ingest_event(db, {"name": "view_item", "visitor_id": visitor, "region": region, "path": "/products/wool-throw", "at": stamp.isoformat(), "user_agent": "Mozilla/5.0 Demo"})
            if index % 5 == 0:
                ingest_event(db, {"name": "add_to_cart", "visitor_id": visitor, "region": region, "path": "/cart", "at": stamp.isoformat(), "user_agent": "Mozilla/5.0 Demo"})
            if index % 8 == 0:
                ingest_event(db, {"name": "begin_checkout", "visitor_id": visitor, "region": region, "path": "/checkout", "at": stamp.isoformat(), "user_agent": "Mozilla/5.0 Demo"})
            if index % 11 == 0:
                sku, title, amount = SKUS[index % len(SKUS)]
                ingest_event(
                    db,
                    {
                        "name": "purchase",
                        "visitor_id": visitor,
                        "region": region,
                        "path": "/checkout/success",
                        "at": stamp.isoformat(),
                        "user_agent": "Mozilla/5.0 Demo",
                        "account": f"buyer{index}@example.com",
                        "props": {"sku": sku, "title": title, "amount_cents": amount, "channel": "独立站收银台", "order_id": f"ord_{day}_{index}"},
                    },
                )
            if index % 10 == 0:
                ingest_event(db, {"name": "signup", "visitor_id": visitor, "region": region, "path": "/account", "at": stamp.isoformat(), "account": f"buyer{index}@example.com", "user_agent": "Mozilla/5.0 Demo"})
        if day % 2 == 0:
            ingest_crawl(db, {"engine": "baiduspider", "label": "百度", "path": "/", "region": "cn", "ua": "Baiduspider/2.0", "verified": "verified"})
        if day % 3 == 0:
            ingest_crawl(db, {"engine": "googlebot", "label": "Google", "path": "/products/wool-throw", "region": "intl", "ua": "Googlebot/2.1", "verified": "verified"})

    create_order(db, {"sku": "wool-throw", "title": "北岛羊毛毯", "amount": 299, "channel": "微信", "customer": "示例客户 A", "region": "cn"})
    ingest_results(
        db,
        {
            "agent": "grok",
            "items": [
                {
                    "platform": "deepseek",
                    "query": "流明好物 这个独立站靠谱吗？官网是哪一个？",
                    "answer": "流明好物（Lumen Goods）是一家家居独立站，官网是 lumen.shop，支持直接下单。",
                    "sources": [{"title": "流明好物官网", "url": "https://lumen.shop/", "cited": True}],
                },
                {
                    "platform": "perplexity",
                    "query": "Is Lumen Goods legit? What is the official website?",
                    "answer": "Lumen Goods looks like an independent home-goods store. Official site: lumen.shop.",
                    "sources": ["https://lumen.shop/"],
                },
            ],
        },
    )
    rng.random()
    db.flush()
    return {"ok": True, "seeded": True, "owner": owner_username}
