from __future__ import annotations

import re

# Crawler / AI-bot taxonomy follows the production Qingjiao console's 37-engine
# list (docs in the SiteLens roadmap): CN search, CN content, CN AI, overseas
# search, overseas AI, plus SEO tooling. Labels stay short for tables; the
# frontend localises them for English screenshots.
BOT_RULES: tuple[tuple[str, str, str], ...] = (
    # 国内搜索
    ("baiduspider", "百度", "国内搜索"),
    ("yisouspider", "神马", "国内搜索"),
    ("bytespider", "头条/抖音", "国内搜索"),
    ("sogou", "搜狗", "国内搜索"),
    ("360spider", "360", "国内搜索"),
    ("petalbot", "花瓣", "国内搜索"),
    # 海外搜索
    ("googlebot", "Google", "海外搜索"),
    ("bingbot", "Bing", "海外搜索"),
    ("yandex", "Yandex", "海外搜索"),
    ("duckduckbot", "DuckDuckGo", "海外搜索"),
    ("bravebot", "Brave", "海外搜索"),
    ("applebot", "Apple", "海外搜索"),
    ("seznambot", "Seznam", "海外搜索"),
    ("amazonbot", "Amazon", "海外搜索"),
    # 国内 AI 模型
    ("deepseek", "DeepSeek", "国内 AI 模型"),
    ("kimi", "Kimi", "国内 AI 模型"),
    ("doubao", "豆包", "国内 AI 模型"),
    # 海外 AI 模型
    ("gptbot", "GPTBot", "海外 AI 模型"),
    ("oai-searchbot", "OpenAI Search", "海外 AI 模型"),
    ("chatgpt-user", "ChatGPT", "海外 AI 模型"),
    ("claudebot", "Claude", "海外 AI 模型"),
    ("anthropic", "Claude", "海外 AI 模型"),
    ("perplexity", "Perplexity", "海外 AI 模型"),
    ("google-extended", "Gemini", "海外 AI 模型"),
    ("meta-externalagent", "Meta AI", "海外 AI 模型"),
    ("ccbot", "Common Crawl", "海外 AI 模型"),
    ("cohere", "Cohere", "海外 AI 模型"),
    ("grok", "Grok", "海外 AI 模型"),
    ("youbot", "You.com", "海外 AI 模型"),
    # SEO 工具
    ("ahrefs", "Ahrefs", "SEO 工具"),
    ("semrush", "Semrush", "SEO 工具"),
    ("mj12bot", "Majestic", "SEO 工具"),
    ("dotbot", "DotBot", "SEO 工具"),
    ("blexbot", "BLEXBot", "SEO 工具"),
    ("diffbot", "Diffbot", "SEO 工具"),
    ("dataforseo", "DataForSEO", "SEO 工具"),
)

# Human referral sources. Order matters: specific platforms before generic
# search/social buckets. CN set mirrors the Qingjiao console; the overseas set
# is what English-speaking operators actually share on (Reddit, Product Hunt,
# Hacker News, X, LinkedIn, YouTube, Quora, Medium, Substack, GitHub...).
SOURCE_RULES: tuple[tuple[str, str], ...] = (
    # AI 回答引用（referrer 直接来自问答产品）
    (r"chatgpt\.com|chat\.openai", "ChatGPT"),
    (r"perplexity", "Perplexity"),
    (r"claude\.ai|anthropic", "Claude"),
    (r"gemini\.google|bard\.google", "Gemini"),
    (r"copilot\.microsoft|bing\.com/chat", "Copilot"),
    (r"deepseek", "DeepSeek"),
    (r"grok\.|x\.ai", "Grok"),
    # 国内内容与社区
    (r"zhihu|知乎", "知乎"),
    (r"xiaohongshu|小红书|xhslink|xhs", "小红书"),
    (r"weixin|wechat|微信|mp\.weixin", "微信"),
    (r"douyin|抖音", "抖音"),
    (r"kuaishou|快手", "快手"),
    (r"bilibili|哔哩|B站", "B站"),
    (r"weibo|微博", "微博"),
    (r"toutiao|头条", "头条"),
    (r"feishu|larksuite|飞书", "飞书"),
    (r"dingtalk|钉钉", "钉钉"),
    (r"csdn", "CSDN"),
    (r"juejin|掘金", "掘金"),
    (r"gitee", "Gitee"),
    (r"sspai|少数派", "少数派"),
    (r"v2ex", "V2EX"),
    (r"douban|豆瓣", "豆瓣"),
    (r"xueqiu|雪球", "雪球"),
    # 国内搜索
    (r"baidu|百度", "百度"),
    (r"quark|夸克", "夸克"),
    (r"sogou|搜狗", "搜狗"),
    (r"sm\.cn|shenma|神马", "神马"),
    (r"so\.com|360", "360搜索"),
    # 海外内容与社区
    (r"producthunt|product hunt", "Product Hunt"),
    (r"news\.ycombinator|hacker news", "Hacker News"),
    (r"reddit", "Reddit"),
    (r"quora", "Quora"),
    (r"medium\.com", "Medium"),
    (r"substack", "Substack"),
    (r"stackoverflow|stack overflow", "Stack Overflow"),
    (r"github", "GitHub"),
    (r"linkedin", "LinkedIn"),
    (r"youtube|youtu\.be", "YouTube"),
    (r"instagram", "Instagram"),
    (r"facebook|fb\.|meta", "Facebook"),
    (r"twitter|(?<![a-z])x\.com|(?<![a-z])x(?![a-z])", "X"),
    (r"tiktok", "TikTok"),
    (r"pinterest", "Pinterest"),
    (r"discord", "Discord"),
    (r"telegram|t\.me", "Telegram"),
    (r"whatsapp", "WhatsApp"),
    (r"threads", "Threads"),
    (r"bluesky|bsky", "Bluesky"),
    (r"dev\.to", "DEV"),
    (r"indiehackers|indie hackers", "Indie Hackers"),
    # 海外搜索
    (r"google\.", "Google"),
    (r"bing\.|必应", "Bing"),
    (r"duckduckgo", "DuckDuckGo"),
    (r"brave", "Brave"),
    (r"ecosia", "Ecosia"),
    (r"yahoo\.", "Yahoo"),
    (r"yandex", "Yandex"),
    (r"naver", "Naver"),
)

# utm_source token -> display label, so ?utm_source=zhihu / =producthunt /
# =reddit Ads read like the platform, not a raw token.
UTM_PLATFORM_NAMES: dict[str, str] = {
    "zhihu": "知乎",
    "xiaohongshu": "小红书",
    "xhs": "小红书",
    "wechat": "微信",
    "weixin": "微信",
    "douyin": "抖音",
    "tiktok": "TikTok",
    "kuaishou": "快手",
    "bilibili": "B站",
    "weibo": "微博",
    "toutiao": "头条",
    "baidu": "百度",
    "quark": "夸克",
    "sogou": "搜狗",
    "feishu": "飞书",
    "lark": "飞书",
    "dingtalk": "钉钉",
    "csdn": "CSDN",
    "juejin": "掘金",
    "github": "GitHub",
    "google": "Google",
    "bing": "Bing",
    "duckduckgo": "DuckDuckGo",
    "brave": "Brave",
    "reddit": "Reddit",
    "producthunt": "Product Hunt",
    "hackernews": "Hacker News",
    "linkedin": "LinkedIn",
    "youtube": "YouTube",
    "instagram": "Instagram",
    "facebook": "Facebook",
    "twitter": "X",
    "x": "X",
    "pinterest": "Pinterest",
    "quora": "Quora",
    "medium": "Medium",
    "substack": "Substack",
    "telegram": "Telegram",
    "whatsapp": "WhatsApp",
    "chatgpt": "ChatGPT",
    "perplexity": "Perplexity",
    "claude": "Claude",
    "gemini": "Gemini",
    "deepseek": "DeepSeek",
    "kimi": "Kimi",
    "doubao": "豆包",
}


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
    match = re.search(r"(?:utm_source|from)=([^\s&#]+)", lowered, flags=re.UNICODE)
    if match:
        value = match.group(1).strip()
        if value:
            key = re.split(r"[^a-z0-9]+", value)[0]
            if key in UTM_PLATFORM_NAMES:
                return UTM_PLATFORM_NAMES[key]
            for token, label in UTM_PLATFORM_NAMES.items():
                if token and token in value:
                    return label
            return value[:80]
    for pattern, label in SOURCE_RULES:
        if re.search(pattern, lowered, re.IGNORECASE):
            return label
    token = (utm or "").strip()
    if token and not referrer and "=" not in token and "://" not in token:
        key = re.split(r"[^a-z0-9]+", token.lower())[0]
        return UTM_PLATFORM_NAMES.get(key, token[:80])
    host = re.sub(r"^https?://", "", referrer or "").split("/")[0]
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
