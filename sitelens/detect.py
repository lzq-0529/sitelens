from __future__ import annotations

import re

BOT_RULES: tuple[tuple[str, str, str], ...] = (
    ("googlebot", "Google", "海外搜索"),
    ("bingbot", "Bing", "海外搜索"),
    ("yandex", "Yandex", "海外搜索"),
    ("baiduspider", "百度", "国内搜索"),
    ("bytespider", "头条/抖音", "内容与社区"),
    ("sogou", "搜狗", "国内搜索"),
    ("360spider", "360", "国内搜索"),
    ("yisouspider", "神马", "国内搜索"),
    ("gptbot", "GPTBot", "海外 AI 模型"),
    ("chatgpt-user", "ChatGPT", "海外 AI 模型"),
    ("claudebot", "Claude", "海外 AI 模型"),
    ("anthropic", "Claude", "海外 AI 模型"),
    ("perplexity", "Perplexity", "海外 AI 模型"),
    ("google-extended", "Gemini", "海外 AI 模型"),
    ("amazonbot", "Amazon", "海外搜索"),
    ("applebot", "Apple", "海外搜索"),
    ("duckduckbot", "DuckDuckGo", "海外搜索"),
    ("semrush", "Semrush", "海外搜索"),
    ("ahrefs", "Ahrefs", "海外搜索"),
    ("petalbot", "Petal", "国内搜索"),
    ("deepseek", "DeepSeek", "国内 AI 模型"),
    ("kimi", "Kimi", "国内 AI 模型"),
    ("doubao", "豆包", "国内 AI 模型"),
)

SOURCE_RULES: tuple[tuple[str, str], ...] = (
    (r"zhihu|知乎", "知乎"),
    (r"xiaohongshu|小红书|xhslink", "小红书"),
    (r"weixin|wechat|微信", "微信"),
    (r"douyin|tiktok|抖音", "抖音"),
    (r"bilibili|B站", "B站"),
    (r"weibo|微博", "微博"),
    (r"toutiao|头条", "头条"),
    (r"baidu|百度", "百度"),
    (r"quark|夸克", "夸克"),
    (r"sogou|搜狗", "搜狗"),
    (r"google\.", "Google"),
    (r"bing\.|必应", "Bing"),
    (r"yahoo\.", "Yahoo"),
    (r"facebook|instagram", "Meta"),
    (r"pinterest", "Pinterest"),
    (r"reddit", "Reddit"),
    (r"utm_source=(\w+)", ""),
)


def classify_agent(user_agent: str) -> tuple[str, str, str]:
    ua = (user_agent or "").lower()
    if not ua:
        return "human", "", ""
    for needle, label, category in BOT_RULES:
        if needle in ua:
            return "bot", label, category
    if "bot" in ua or "spider" in ua or "crawler" in ua:
        return "bot", "未知爬虫", "其他"
    return "human", "", ""


def source_of(referrer: str, utm: str = "") -> str:
    blob = f"{utm} {referrer}".strip()
    if not blob:
        return "直接访问"
    lowered = blob.lower()
    match = re.search(r"(?:utm_source|from)=([a-z0-9_\-]+)", lowered)
    if match:
        return match.group(1)
    for pattern, label in SOURCE_RULES:
        if re.search(pattern, lowered, re.IGNORECASE):
            return label or blob
    host = re.sub(r"^https?://", "", referrer).split("/")[0]
    return host or "直接访问"


def device_of(user_agent: str) -> str:
    ua = user_agent or ""
    if not ua:
        return "未知设备"
    if re.search(r"iPhone|Android|Mobile", ua):
        browser = "Safari" if "Safari" in ua and "Chrome" not in ua else "Chrome" if "Chrome" in ua else "Mobile"
        return f"手机 / {browser}"
    if "iPad" in ua or "Tablet" in ua:
        return "平板"
    if "Macintosh" in ua:
        return "Mac / Safari" if "Safari" in ua and "Chrome" not in ua else "Mac / Chrome"
    if "Windows" in ua:
        return "Windows / Edge" if "Edg" in ua else "Windows / Chrome"
    if "Linux" in ua:
        return "Linux"
    return ua[:80]
