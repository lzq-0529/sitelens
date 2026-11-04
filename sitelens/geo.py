from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import GeoCheck, Setting, utcnow
from .siteconfig import load_site

GEO_PLATFORMS: tuple[dict[str, Any], ...] = (
    {"id": "deepseek", "label": "DeepSeek 网页", "region": "cn", "region_label": "国内", "url": "https://chat.deepseek.com/", "login": "常可免登"},
    {"id": "doubao", "label": "豆包", "region": "cn", "region_label": "国内", "url": "https://www.doubao.com/", "login": "常可免登"},
    {"id": "kimi", "label": "Kimi", "region": "cn", "region_label": "国内", "url": "https://kimi.moonshot.cn/", "login": "常可免登"},
    {"id": "qwen", "label": "通义千问", "region": "cn", "region_label": "国内", "url": "https://tongyi.aliyun.com/", "login": "常可免登"},
    {"id": "yiyan", "label": "文心一言", "region": "cn", "region_label": "国内", "url": "https://yiyan.baidu.com/", "login": "常可免登"},
    {"id": "chatglm", "label": "智谱清言", "region": "cn", "region_label": "国内", "url": "https://chatglm.cn/", "login": "常可免登"},
    {"id": "yuanbao", "label": "腾讯元宝", "region": "cn", "region_label": "国内", "url": "https://yuanbao.tencent.com/", "login": "常可免登"},
    {"id": "metaso", "label": "秘塔 AI", "region": "cn", "region_label": "国内", "url": "https://metaso.cn/", "login": "常可免登"},
    {"id": "tiangong", "label": "天工", "region": "cn", "region_label": "国内", "url": "https://www.tiangong.cn/", "login": "常可免登"},
    {"id": "perplexity", "label": "Perplexity", "region": "intl", "region_label": "海外", "url": "https://www.perplexity.ai/", "login": "额度内可问"},
    {"id": "chatgpt", "label": "ChatGPT", "region": "intl", "region_label": "海外", "url": "https://chatgpt.com/", "login": "多半要登"},
    {"id": "gemini", "label": "Google Gemini", "region": "intl", "region_label": "海外", "url": "https://gemini.google.com/", "login": "多半要登"},
    {"id": "copilot", "label": "Microsoft Copilot", "region": "intl", "region_label": "海外", "url": "https://copilot.microsoft.com/", "login": "偶发游客"},
    {"id": "claude", "label": "Claude.ai", "region": "intl", "region_label": "海外", "url": "https://claude.ai/", "login": "要登"},
    {"id": "grok", "label": "Grok", "region": "intl", "region_label": "海外", "url": "https://grok.com/", "login": "要登"},
)

_PLATFORM_MAP = {item["id"]: item for item in GEO_PLATFORMS}
_ALIASES = {
    "deepseek": "deepseek",
    "deepseek网页": "deepseek",
    "deepseek 网页": "deepseek",
    "doubao": "doubao",
    "豆包": "doubao",
    "kimi": "kimi",
    "moonshot": "kimi",
    "qwen": "qwen",
    "tongyi": "qwen",
    "通义千问": "qwen",
    "千问": "qwen",
    "yiyan": "yiyan",
    "文心一言": "yiyan",
    "chatglm": "chatglm",
    "智谱清言": "chatglm",
    "yuanbao": "yuanbao",
    "腾讯元宝": "yuanbao",
    "metaso": "metaso",
    "秘塔": "metaso",
    "tiangong": "tiangong",
    "天工": "tiangong",
    "perplexity": "perplexity",
    "chatgpt": "chatgpt",
    "openai": "chatgpt",
    "gemini": "gemini",
    "copilot": "copilot",
    "claude": "claude",
    "grok": "grok",
    "xai": "grok",
    "muse": "chatgpt",
}

PROMPT_KEY = "geo_prompts"


def normalize_platform(raw: str) -> str:
    key = str(raw or "").strip().lower()
    if key in _PLATFORM_MAP:
        return key
    if key in _ALIASES:
        return _ALIASES[key]
    for alias, pid in _ALIASES.items():
        if alias in key:
            return pid
    return key or "deepseek"


def default_prompts(site: dict[str, Any]) -> dict[str, list[str]]:
    brand = site.get("brand") or "这个品牌"
    category = site.get("category") or "这个品类"
    return {
        "cn": [
            f"{brand} 这个独立站靠谱吗？官网是哪一个？",
            f"想买{category}，有哪些独立站值得推荐？",
            f"{brand} 和同类品牌怎么选？去哪里下单是正品？",
            f"{category} 独立站有哪些？怎么判断是不是官方店？",
            f"最近有人提到 {brand} 吗？口碑怎么样？",
        ],
        "intl": [
            f"Is {brand} legit? What is the official website?",
            f"Best independent stores for {category}?",
            f"{brand} vs competitors — where should I order?",
            f"How to find the official {brand} store and avoid fake sites?",
        ],
    }


def geo_prompts(db: Session) -> dict[str, list[str]]:
    site = load_site(db)
    row = db.scalar(select(Setting).where(Setting.key == PROMPT_KEY))
    if row is not None:
        try:
            stored = json.loads(row.value or "{}")
        except json.JSONDecodeError:
            stored = {}
        if isinstance(stored, dict) and (stored.get("cn") or stored.get("intl")):
            return {
                "cn": [str(item).strip() for item in (stored.get("cn") or []) if str(item).strip()],
                "intl": [str(item).strip() for item in (stored.get("intl") or []) if str(item).strip()],
            }
    return default_prompts(site)


def save_geo_prompts(db: Session, payload: dict[str, Any]) -> dict[str, list[str]]:
    current = geo_prompts(db)
    action = str(payload.get("action") or "save").strip().lower()
    if action == "reset":
        next_prompts = default_prompts(load_site(db))
    elif action == "add":
        region = "intl" if str(payload.get("region") or "cn").lower() == "intl" else "cn"
        lines = [line.strip() for line in str(payload.get("query") or payload.get("prompt") or "").splitlines() if line.strip()]
        if not lines:
            raise ValueError("请输入要添加的提问词条")
        merged = list(current[region])
        for line in lines:
            if line not in merged:
                merged.append(line)
        next_prompts = {**current, region: merged}
    elif action == "delete":
        region = "intl" if str(payload.get("region") or "cn").lower() == "intl" else "cn"
        target = str(payload.get("query") or payload.get("prompt") or "").strip()
        next_prompts = {**current, region: [item for item in current[region] if item != target]}
    else:
        next_prompts = {}
        for region in ("cn", "intl"):
            if region not in payload:
                next_prompts[region] = current[region]
                continue
            value = payload[region]
            if isinstance(value, str):
                lines = [line.strip() for line in value.splitlines() if line.strip() and not line.startswith("#")]
            elif isinstance(value, list):
                lines = [str(item).strip() for item in value if str(item).strip()]
            else:
                lines = current[region]
            next_prompts[region] = list(dict.fromkeys(lines))
    if not next_prompts.get("cn") and not next_prompts.get("intl"):
        raise ValueError("至少需要保留一条提问词")
    blob = json.dumps(next_prompts, ensure_ascii=False)
    row = db.scalar(select(Setting).where(Setting.key == PROMPT_KEY))
    if row is None:
        db.add(Setting(key=PROMPT_KEY, value=blob, updated_at=utcnow()))
    else:
        row.value = blob
        row.updated_at = utcnow()
    db.flush()
    return next_prompts


def _aware(value: datetime | None, fallback: datetime | None = None) -> datetime:
    if value is None:
        return fallback if fallback is not None else utcnow()
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _host(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower().removeprefix("www.")
    except ValueError:
        return ""


def _as_source_list(raw_sources: Any) -> list[Any]:
    if isinstance(raw_sources, list):
        return raw_sources
    if isinstance(raw_sources, tuple):
        return list(raw_sources)
    if isinstance(raw_sources, str) and raw_sources.strip():
        return [raw_sources.strip()]
    return []


def score_item(query: str, answer: str, raw_sources: list[Any], site: dict[str, Any]) -> dict[str, Any]:
    sources: list[dict[str, Any]] = []
    for index, item in enumerate(_as_source_list(raw_sources), start=1):
        if isinstance(item, str):
            sources.append({"rank": index, "url": item.strip(), "title": item.strip(), "cited": True})
            continue
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or item.get("link") or item.get("href") or "").strip()
        title = str(item.get("title") or item.get("name") or url).strip()
        raw_rank = item.get("rank") if item.get("rank") is not None else item.get("index")
        try:
            rank = max(1, int(raw_rank)) if raw_rank is not None else index
        except (TypeError, ValueError, OverflowError):
            rank = index
        if url or title:
            sources.append({"rank": rank, "url": url, "title": title, "cited": bool(item.get("cited", True))})

    domains = [str(item).lower().removeprefix("www.") for item in (site.get("domains") or [])]
    owned_urls = [str(item).lower() for item in (site.get("owned_urls") or [])]
    aliases = [site.get("brand") or ""] + list(site.get("brand_aliases") or [])
    aliases = [item for item in aliases if item]
    keywords = [item for item in (site.get("keywords") or []) if item]
    competitors = [item for item in (site.get("competitors") or []) if item]

    citations = []
    owned = []
    for source in sources:
        host = _host(source["url"])
        blob = f"{source['url']} {source['title']}".lower()
        domain_hit = bool(host and any(host == domain or host.endswith("." + domain) for domain in domains if domain))
        url_hit = any(marker in blob for marker in owned_urls if marker)
        if domain_hit or url_hit:
            citations.append({"url": source["url"], "rank": source["rank"]})
            owned.append(
                {
                    "rank": source["rank"],
                    "kind": "domain" if domain_hit else "article",
                    "url": source["url"],
                    "title": source["title"],
                    "cited": source["cited"],
                }
            )

    answer_text = str(answer or "")
    if not citations:
        for domain in domains:
            if domain and domain in answer_text.lower():
                citations.append({"url": f"https://{domain}", "rank": 1})
                owned.insert(0, {"rank": 1, "kind": "domain", "url": f"https://{domain}", "title": "正文直接提及官网", "cited": True})
                break

    brand_re = "|".join(re.escape(item) for item in aliases) if aliases else r"$a"
    keyword_re = "|".join(re.escape(item) for item in keywords) if keywords else r"$a"
    brand_mentioned = bool(re.search(brand_re, answer_text, re.IGNORECASE)) if aliases else False
    feature_mentioned = bool(re.search(keyword_re, answer_text, re.IGNORECASE)) if keywords else False
    blob = answer_text + " " + " ".join(f"{item.get('title', '')} {item.get('url', '')}" for item in sources)
    mentioned_competitors = [name for name in competitors if name and re.search(re.escape(name), blob, re.IGNORECASE)]
    return {
        "query": str(query or "").strip(),
        "cited": bool(citations),
        "retrieved": bool(citations),
        "citations": citations,
        "ownedMatches": owned,
        "ownedCited": any(item["cited"] for item in owned) or bool(citations),
        "ownedRetrieved": bool(owned),
        "brandMentioned": brand_mentioned,
        "featureMentioned": feature_mentioned,
        "competitorsMentioned": mentioned_competitors,
        "answerExcerpt": re.sub(r"\s+", " ", answer_text).strip()[:500],
        "rawSources": sources[:12],
        "answer": answer_text[:2000],
        "error": None,
    }


def ingest_results(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    site = load_site(db)
    source_mode = str(payload.get("source_mode") or payload.get("agent") or "grok").strip() or "grok"
    grouped: dict[str, dict[str, Any]] = {}
    if isinstance(payload.get("items"), list):
        for item in payload["items"]:
            if not isinstance(item, dict):
                continue
            pid = normalize_platform(item.get("platform") or item.get("engine") or payload.get("platform") or "deepseek")
            bucket = grouped.setdefault(pid, {"model": item.get("model") or payload.get("model") or "网页默认模型", "rows": []})
            bucket["rows"].append(item)
    elif isinstance(payload.get("platforms"), dict):
        for raw_id, data in payload["platforms"].items():
            if not isinstance(data, dict):
                continue
            pid = normalize_platform(raw_id)
            bucket = grouped.setdefault(pid, {"model": data.get("model") or "网页默认模型", "rows": []})
            bucket["rows"].extend(data.get("results") or data.get("items") or [])
    else:
        pid = normalize_platform(payload.get("platform") or payload.get("engine") or "deepseek")
        rows = payload.get("results")
        if not isinstance(rows, list):
            rows = [payload] if payload.get("query") and (payload.get("answer") is not None or payload.get("sources") is not None) else []
        grouped[pid] = {"model": str(payload.get("model") or "网页默认模型").strip(), "rows": rows}

    if not grouped or not any(bucket["rows"] for bucket in grouped.values()):
        raise ValueError("请提供至少一条问答结果（包含 platform、query、answer 或 sources）")

    updated = []
    now = utcnow()
    for pid, bundle in grouped.items():
        if not bundle["rows"]:
            continue
        for item in bundle["rows"]:
            if not isinstance(item, dict):
                continue
            query = str(item.get("query") or item.get("prompt") or item.get("question") or "").strip()
            if not query:
                continue
            answer = str(item.get("answer") or item.get("response") or item.get("content") or "")
            sources = item.get("sources") or item.get("citations") or item.get("references") or item.get("urls") or []
            scored = score_item(query, answer, sources, site)
            existing = db.scalar(select(GeoCheck).where(GeoCheck.platform == pid, GeoCheck.query == query))
            blob = json.dumps(scored, ensure_ascii=False)
            if existing is None:
                db.add(
                    GeoCheck(
                        platform=pid,
                        model=str(bundle["model"] or "网页默认模型"),
                        source_mode=source_mode,
                        query=query,
                        answer=answer[:8000],
                        scored=blob,
                        updated_at=now,
                    )
                )
            else:
                existing.model = str(bundle["model"] or existing.model)
                existing.source_mode = source_mode
                existing.answer = answer[:8000]
                existing.scored = blob
                existing.updated_at = now
        updated.append(pid)
    db.flush()
    report = geo_report(db)
    return {"ok": True, "updated_platforms": updated, "updated_at": now.isoformat(), "summary": report["summary"]}


def _interval_days(schedule: str) -> int:
    return 1 if schedule == "daily" else 7


def geo_report(db: Session) -> dict[str, Any]:
    site = load_site(db)
    schedule = site.get("geo_schedule") or "weekly"
    interval = _interval_days(schedule)
    rows = list(db.scalars(select(GeoCheck)))
    by_platform: dict[str, list[GeoCheck]] = {}
    for row in rows:
        by_platform.setdefault(row.platform, []).append(row)

    now = utcnow()
    platforms = []
    detail_rows = []
    owned = 0
    brand = 0
    total_queries = 0
    competitor_counts: Counter = Counter()
    latest = None
    for spec in GEO_PLATFORMS:
        checks = by_platform.get(spec["id"]) or []
        checks.sort(key=lambda item: _aware(item.updated_at, now), reverse=True)
        last = _aware(checks[0].updated_at) if checks else None
        due = last is None or (now - last) >= timedelta(days=interval)
        cited = 0
        best_rank = None
        brand_hits = 0
        for check in checks:
            try:
                scored = json.loads(check.scored or "{}")
            except json.JSONDecodeError:
                scored = {}
            total_queries += 1
            if scored.get("ownedCited") or scored.get("cited"):
                owned += 1
                cited += 1
            if scored.get("brandMentioned"):
                brand += 1
                brand_hits += 1
            for comp in scored.get("competitorsMentioned") or []:
                if comp:
                    competitor_counts[str(comp)] += 1
            ranks = [int(item.get("rank") or 0) for item in scored.get("citations") or [] if item.get("rank")]
            if ranks:
                best_rank = min(best_rank or ranks[0], min(ranks))
            detail_rows.append(
                {
                    "id": check.id,
                    "engine": spec["id"],
                    "engine_label": spec["label"],
                    "region": spec["region"],
                    "query": check.query,
                    "answer_excerpt": scored.get("answerExcerpt") or check.answer[:180],
                    "cited": bool(scored.get("cited")),
                    "brand_mentioned": bool(scored.get("brandMentioned")),
                    "competitors": scored.get("competitorsMentioned") or [],
                    "best_rank": min(ranks) if ranks else None,
                    "updated_at": check.updated_at.isoformat() if check.updated_at else None,
                    "source_mode": check.source_mode,
                    "model": check.model,
                }
            )
        if last and (latest is None or last > _aware(latest)):
            latest = last
        platforms.append(
            {
                **spec,
                "schedule": "每日" if schedule == "daily" else "每周",
                "interval_days": interval,
                "tested": bool(checks),
                "is_due": due,
                "updated_at": last.isoformat() if last else "",
                "query_count": len(checks),
                "direct_cited": cited,
                "brand_mentions": brand_hits,
                "best_rank": best_rank,
            }
        )
    return {
        "updated_at": latest.isoformat() if latest else None,
        "schedule": schedule,
        "site": {"brand": site.get("brand"), "domains": site.get("domains") or []},
        "summary": {
            "total_platforms": len(GEO_PLATFORMS),
            "tested_platforms": sum(1 for item in platforms if item["tested"]),
            "due_platforms": sum(1 for item in platforms if item["is_due"]),
            "total_queries": total_queries,
            "owned_cited_count": owned,
            "brand_mention_count": brand,
            "owned_coverage_pct": round((owned / total_queries) * 100) if total_queries else 0,
            "brand_mention_pct": round((brand / total_queries) * 100) if total_queries else 0,
            "visibility_score": round(((brand / total_queries) * 0.5 + (owned / total_queries) * 0.5) * 100) if total_queries else 0,
            "competitors": [{"name": name, "mentions": count} for name, count in competitor_counts.most_common(8)],
            "share_of_voice_pct": round((brand / (brand + sum(competitor_counts.values()))) * 100) if (brand + sum(competitor_counts.values())) else 0,
        },
        "platforms": platforms,
        "rows": detail_rows,
        "prompts": geo_prompts(db),
    }


def geo_tasks(db: Session) -> dict[str, Any]:
    report = geo_report(db)
    prompts = report["prompts"]
    due = [item for item in report["platforms"] if item["is_due"]]
    site = load_site(db)
    return {
        "generated_at": report["updated_at"],
        "due_count": len(due),
        "due_platforms": [
            {
                "id": item["id"],
                "label": item["label"],
                "region": item["region_label"],
                "url": item["url"],
                "login": item["login"],
                "schedule": item["schedule"],
                "last_checked_at": item["updated_at"] or None,
                "prompts": prompts["cn"] if item["region"] == "cn" else prompts["intl"],
            }
            for item in due
        ],
        "all_platforms": report["platforms"],
        "prompts": prompts,
        "tracked_targets": {
            "brand": site.get("brand"),
            "domains": site.get("domains") or [],
            "aliases": site.get("brand_aliases") or [],
            "owned_urls": site.get("owned_urls") or [],
        },
        "agents": ["grok", "muse", "custom"],
    }
