from __future__ import annotations

import random
import secrets
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from .analytics import ingest_crawl, ingest_event
from .auth import OWNER, create_user
from .geo import ingest_results
from .models import Event, User, utcnow
from .orders import create_order
from .siteconfig import load_site, save_site

# Demo store: 流明好物 / Lumen Goods. The source *mix* is modelled on the real
# qingjiaolab.com console (Zhihu-heavy in China, Google-heavy overseas, with a
# long tail of content/AI referrals), but every person here is invented:
# accounts are @example.com, IPs are RFC 5737 documentation ranges
# (192.0.2.0/24, 198.51.100.0/24, 203.0.113.0/24) and the console masks the
# last IP octet on display anyway. No real Qingjiao visitor data is shipped.
CN_SOURCES: tuple[tuple[str, str, int], ...] = (
    # (display source, referrer URL, weight)
    ("知乎", "https://www.zhihu.com/question/501122333", 16),
    ("百度", "https://www.baidu.com/s?wd=亚麻床品", 14),
    ("小红书", "https://www.xiaohongshu.com/explore/demo-note", 12),
    ("微信", "https://mp.weixin.qq.com/s/demo-article", 10),
    ("直接访问", "", 10),
    ("抖音", "https://www.douyin.com/video/demo", 7),
    ("夸克", "https://www.quark.cn/s?q=羊毛毯", 5),
    ("B站", "https://www.bilibili.com/video/BV-demo", 5),
    ("头条", "https://www.toutiao.com/article/demo", 4),
    ("搜狗", "https://www.sogou.com/web?query=床品", 3),
    ("微博", "https://weibo.com/demo", 3),
    ("快手", "https://www.kuaishou.com/short-video/demo", 3),
    ("CSDN", "https://blog.csdn.net/demo/article", 2),
    ("掘金", "https://juejin.cn/post/demo", 2),
    ("飞书", "https://www.feishu.cn/demo", 2),
    ("DeepSeek", "https://chat.deepseek.com/demo", 2),
    ("豆包", "https://www.doubao.com/chat/demo", 1),
    ("神马", "https://m.sm.cn/s?q=床品四件套", 1),
)

INTL_SOURCES: tuple[tuple[str, str, int], ...] = (
    ("Google", "https://www.google.com/search?q=linen+bedding+set", 18),
    ("直接访问", "", 9),
    ("Reddit", "https://www.reddit.com/r/Bedding/demo", 8),
    ("Instagram", "https://www.instagram.com/p/demo", 8),
    ("Pinterest", "https://www.pinterest.com/pin/demo", 7),
    ("YouTube", "https://www.youtube.com/watch?v=demo", 6),
    ("Product Hunt", "https://www.producthunt.com/products/lumen-goods", 5),
    ("Facebook", "https://www.facebook.com/demo", 5),
    ("X", "https://x.com/lumengoods/status/demo", 5),
    ("TikTok", "https://www.tiktok.com/@lumengoods/video/demo", 5),
    ("Bing", "https://www.bing.com/search?q=wool+throw", 4),
    ("Hacker News", "https://news.ycombinator.com/item?id=demo", 3),
    ("LinkedIn", "https://www.linkedin.com/company/demo", 3),
    ("DuckDuckGo", "https://duckduckgo.com/?q=linen+bedding", 3),
    ("Quora", "https://www.quora.com/demo-answer", 2),
    ("Medium", "https://medium.com/@demo/linen-guide", 2),
    ("Substack", "https://demo.substack.com/p/linen", 2),
    ("Perplexity", "https://www.perplexity.ai/search/demo", 2),
    ("ChatGPT", "https://chatgpt.com/share/demo", 2),
    ("GitHub", "https://github.com/demo", 1),
    ("Brave", "https://search.brave.com/search?q=wool+throw", 1),
    ("Telegram", "https://t.me/demo", 1),
)

# Kept for backwards compatibility with older imports.
SOURCES = tuple(name for name, _url, _w in CN_SOURCES + INTL_SOURCES)

PATHS = (
    "/",
    "/products/linen-set",
    "/products/wool-throw",
    "/products/pour-over",
    "/collections/home",
    "/collections/bedding",
    "/journal/linen-care-guide",
    "/journal/wool-throw-review",
    "/about",
    "/cart",
    "/checkout",
)
SKUS = (
    ("linen-set", "亚麻床品四件套", 45900),
    ("wool-throw", "北岛羊毛毯", 29900),
    ("pour-over", "手冲咖啡套装", 18900),
)

USER_AGENTS = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.49",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 ZhihuHybrid/1.0",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36 Edg/126.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
)

CRAWLERS: tuple[tuple[str, str, str, str], ...] = (
    # (engine slug, label, region, UA token)
    ("baidu", "百度", "cn", "Baiduspider/2.0"),
    ("google", "Google", "intl", "Googlebot/2.1"),
    ("bing", "Bing", "intl", "bingbot/2.0"),
    ("bytespider", "头条/抖音", "cn", "Bytespider/1.0"),
    ("sogou", "搜狗", "cn", "Sogou web spider/4.0"),
    ("360", "360", "cn", "360Spider/1.0"),
    ("petal", "花瓣", "cn", "PetalBot/1.0"),
    ("shenma", "神马", "cn", "YisouSpider/1.0"),
    ("duckduckgo", "DuckDuckGo", "intl", "DuckDuckBot/1.1"),
    ("yandex", "Yandex", "intl", "YandexBot/3.0"),
    ("brave", "Brave", "intl", "Bravebot/1.0"),
    ("apple", "Apple", "intl", "Applebot/0.1"),
    ("gptbot", "GPTBot", "intl", "GPTBot/1.2"),
    ("chatgpt", "ChatGPT", "intl", "ChatGPT-User/1.0"),
    ("claude", "Claude", "intl", "ClaudeBot/1.0"),
    ("perplexity", "Perplexity", "intl", "PerplexityBot/1.0"),
    ("gemini", "Gemini", "intl", "Google-Extended/1.0"),
    ("ahrefs", "Ahrefs", "intl", "AhrefsBot/7.0"),
    ("semrush", "Semrush", "intl", "SemrushBot/7.0"),
    ("deepseek", "DeepSeek", "cn", "DeepSeekBot/1.0"),
    ("commoncrawl", "Common Crawl", "intl", "CCBot/2.0"),
    ("meta", "Meta AI", "intl", "meta-externalagent/1.1"),
)

GEO_ITEMS: tuple[dict, ...] = (
    {"platform": "deepseek", "query": "流明好物 这个独立站靠谱吗？官网是哪一个？", "answer": "流明好物（Lumen Goods）是一家家居独立站，官网是 lumen.shop，主营亚麻床品和羊毛毯，支持直接下单。", "sources": [{"title": "流明好物官网", "url": "https://lumen.shop/", "cited": True}]},
    {"platform": "doubao", "query": "亚麻床品四件套哪个独立站能买到？", "answer": "可以看看流明好物 lumen.shop 的亚麻床品四件套，页面有材质和洗护说明。", "sources": ["https://lumen.shop/products/linen-set"]},
    {"platform": "kimi", "query": "北岛羊毛毯是哪家店的？", "answer": "北岛羊毛毯是流明好物（lumen.shop）的商品之一，同店还有手冲咖啡套装。", "sources": ["https://lumen.shop/products/wool-throw"]},
    {"platform": "qwen", "query": "Lumen Goods 官网是什么？", "answer": "Lumen Goods 中文名流明好物，官网 lumen.shop。", "sources": ["https://lumen.shop/"]},
    {"platform": "yiyan", "query": "流明好物卖什么？", "answer": "流明好物是家居生活方式独立站，主要卖床品、羊毛毯和咖啡器具。", "sources": []},
    {"platform": "perplexity", "query": "Is Lumen Goods legit? What is the official website?", "answer": "Lumen Goods looks like an independent home-goods store. Official site: lumen.shop, with linen bedding and wool throws.", "sources": ["https://lumen.shop/"]},
    {"platform": "chatgpt", "query": "Where can I buy the North Island wool throw?", "answer": "The North Island wool throw is listed by Lumen Goods at lumen.shop/products/wool-throw.", "sources": ["https://lumen.shop/products/wool-throw"]},
    {"platform": "gemini", "query": "Best independent store for linen bedding sets?", "answer": "Lumen Goods (lumen.shop) sells a linen bedding set with care guides; larger marketplaces carry wider ranges.", "sources": ["https://lumen.shop/products/linen-set"]},
    {"platform": "claude", "query": "What does Lumen Goods sell?", "answer": "Lumen Goods is a home-goods independent store: bedding, wool throws, and pour-over coffee sets.", "sources": []},
    {"platform": "grok", "query": "Lumen Goods official site?", "answer": "Official site is lumen.shop (流明好物).", "sources": ["https://lumen.shop/"]},
    {"platform": "copilot", "query": "Lumen Goods pour-over coffee set price?", "answer": "Lumen Goods lists a pour-over coffee set on lumen.shop; check the product page for current pricing.", "sources": ["https://lumen.shop/products/pour-over"]},
    {"platform": "metaso", "query": "流明好物和示例竞品哪个好？", "answer": "流明好物 lumen.shop 偏家居生活方式，示例竞品偏百货，两家品类重心不同。", "sources": []},
)


def _pick(rng: random.Random, table):
    names = [row[0] for row in table]
    weights = [row[2] for row in table]
    chosen = rng.choices(names, weights=weights, k=1)[0]
    return next(row for row in table if row[0] == chosen)


def _demo_ip(rng: random.Random, region: str) -> str:
    # RFC 5737 documentation ranges only — never a real person's address.
    net = rng.choice(("192.0.2", "198.51.100", "203.0.113")) if region == "intl" else rng.choice(("198.51.100", "203.0.113"))
    return f"{net}.{rng.randint(2, 250)}"


def seed_demo(db: Session, *, owner_username: str = "owner", owner_password: str = "sitelens-demo") -> dict:
    if db.scalar(select(User).where(User.username == owner_username)) is None:
        create_user(db, owner_username, owner_password, role=OWNER, display_name="站点管理员")
    current = load_site(db)
    save_site(
        db,
        {
            "brand": "流明好物",
            "brand_aliases": ["Lumen Goods", "lumen.shop"],
            "category": "家居与生活方式",
            "domains": ["lumen.shop", "www.lumen.shop"],
            "cn_hosts": ["lumen.shop", "www.lumen.shop"],
            "intl_hosts": ["intl.lumen.shop"],
            "competitors": ["示例竞品"],
            "collect_token": current.get("collect_token") or "slcol_" + secrets.token_urlsafe(18),
            "hook_token": current.get("hook_token") or "slhook_" + secrets.token_urlsafe(18),
        },
    )
    if db.scalar(select(Event.id)) is not None:
        return {"ok": True, "seeded": False, "message": "已有事件数据，跳过演示填充"}

    rng = random.Random(42)
    now = utcnow()
    for day in range(28):
        stamp = now - timedelta(days=27 - day)
        visitors = 26 + (day % 7) * 4 + rng.randint(0, 6)
        for index in range(visitors):
            region = "intl" if rng.random() < 0.38 else "cn"
            source, referrer, _weight = _pick(rng, INTL_SOURCES if region == "intl" else CN_SOURCES)
            visitor = f"demo_{day}_{index}"
            path = rng.choice(PATHS)
            ua = rng.choice(USER_AGENTS)
            ip = _demo_ip(rng, region)
            account = f"buyer{index}@example.com" if index % 7 == 0 else ""
            ingest_event(
                db,
                {
                    "name": "pageview",
                    "visitor_id": visitor,
                    "region": region,
                    "path": path,
                    "referrer": referrer,
                    "source": source,
                    "at": stamp.isoformat(),
                    "user_agent": ua,
                    "ip": ip,
                    "account": account,
                },
            )
            for _extra in range(rng.randint(0, 2)):
                ingest_event(db, {"name": "pageview", "visitor_id": visitor, "region": region, "path": rng.choice(PATHS), "referrer": referrer, "source": source, "at": stamp.isoformat(), "user_agent": ua, "ip": ip})
            if index % 3 != 2:
                sku, _title, _amount = SKUS[index % len(SKUS)]
                ingest_event(db, {"name": "view_item", "visitor_id": visitor, "region": region, "path": f"/products/{sku}", "at": stamp.isoformat(), "user_agent": ua, "ip": ip})
            if index % 4 == 0:
                ingest_event(db, {"name": "add_to_cart", "visitor_id": visitor, "region": region, "path": "/cart", "at": stamp.isoformat(), "user_agent": ua, "ip": ip})
            if index % 7 == 0:
                ingest_event(db, {"name": "begin_checkout", "visitor_id": visitor, "region": region, "path": "/checkout", "at": stamp.isoformat(), "user_agent": ua, "ip": ip})
            if index % 10 == 0:
                sku, title, amount = SKUS[index % len(SKUS)]
                ingest_event(
                    db,
                    {
                        "name": "purchase",
                        "visitor_id": visitor,
                        "region": region,
                        "path": "/checkout/success",
                        "at": stamp.isoformat(),
                        "user_agent": ua,
                        "ip": ip,
                        "account": f"buyer{index}@example.com",
                        "props": {"sku": sku, "title": title, "amount_cents": amount, "channel": "独立站收银台", "order_id": f"ord_{day}_{index}"},
                    },
                )
            if index % 9 == 0:
                ingest_event(db, {"name": "signup", "visitor_id": visitor, "region": region, "path": "/account", "at": stamp.isoformat(), "account": f"buyer{index}@example.com", "user_agent": ua, "ip": ip})
        # A rotating handful of crawlers every day, so the SEO tab is dense.
        for engine, label, region, ua in rng.sample(CRAWLERS, k=6):
            ingest_crawl(
                db,
                {
                    "engine": engine,
                    "label": label,
                    "path": rng.choice(PATHS),
                    "region": region,
                    "ua": f"Mozilla/5.0 (compatible; {ua}; +https://example.com/bot)",
                    "ip": _demo_ip(rng, region),
                    "verified": "verified" if rng.random() < 0.7 else "unchecked",
                    "status": 200 if rng.random() < 0.92 else 404,
                },
            )

    create_order(db, {"sku": "wool-throw", "title": "北岛羊毛毯", "amount": 299, "channel": "微信", "customer": "demo-a@example.com", "region": "cn"})
    create_order(db, {"sku": "linen-set", "title": "Linen bedding set", "amount": 459, "channel": "Stripe", "customer": "demo-b@example.com", "region": "intl"})
    create_order(db, {"sku": "pour-over", "title": "Pour-over coffee set", "amount": 189, "channel": "PayPal", "customer": "demo-c@example.com", "region": "intl"})
    ingest_results(db, {"agent": "grok", "items": list(GEO_ITEMS)})
    db.flush()
    site = load_site(db)
    return {
        "ok": True,
        "seeded": True,
        "owner": owner_username,
        "collect_token": site.get("collect_token") or "",
        "hook_token": site.get("hook_token") or "",
    }
