# Get a store live in 30 minutes

You should see visitors, identified users, real orders, and a GEO / daily alert loop. No extra pages.

## 0. Start (5 min)

Docker:

```bash
cp .env.example .env
docker compose up -d --build
docker compose exec sitelens python -m sitelens.manage create-owner --username you --password 'ten-chars-min'
```

Or local:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export SITELENS_DATA_DIR="$PWD/.local"
python -m sitelens.manage create-owner --username you
(cd web && npm ci && npm run build)
python -m sitelens
```

Open http://127.0.0.1:8788. Demo data: `python -m sitelens.manage seed-demo` (`owner` / `sitelens-demo`).

Production must set `SITELENS_ENV=production` or collect stays open. Reverse proxy / HTTPS: [deploy.md](deploy.md).

## 1. Settings: brand and both hosts (5 min)

In **接入设置**:

1. Brand, aliases, keywords
2. **cn_hosts** and **intl_hosts** on separate lines
3. Save and copy the tracker snippet (`data-token` included)

`domains` alone is not enough. Missing `intl_hosts` marks every overseas host as China.

## SEO is automatic

The snippet is enough. Open **站点 / SEO / GEO**:

- **搜索引擎与 AI 抓取** — Baidu, Google, GPTBot, Ahrefs, Semrush, DeepSeek, and the rest, plus which paths they hit
- Sources — Zhihu, 小红书, WeChat, Douyin, Baidu, Google, and `utm_source`
- **爬虫日志** — path, status, IP
- Switch to “只看真人” so crawlers do not inflate conversion

Search Console can stay as a complement. Day-to-day crawl visibility lives here.

## 2. Identity (5 min)

The snippet records pageviews. After login/signup you must send the account or the visitors page stays empty:

```html
<script defer src="https://sitelens.yourdomain.com/tracker.js" data-region="cn" data-token="slcol_..."></script>
<script>
  sitelens.identify(currentUser.email);
</script>
```

The backend reads top-level `account` / `email` and `props.account`. The tracker now sends both.

## 3. Real orders (5 min)

Pick one. Do not rely on manual bookkeeping.

- **Shopify**: notification URL = `/api/hooks/shopify`, secret = `shopify_secret`, topic `orders/paid`
- **WooCommerce**: `/api/hooks/woocommerce` + `woo_secret`
- **Generic**:

```bash
curl -X POST https://sitelens.yourdomain.com/api/hooks/order \
  -H 'content-type: application/json' \
  -H "x-sitelens-token: slhook_..." \
  -d '{"id":"A1001","amount":199,"title":"Wool throw","sku":"wool-1","customer":"ada@shop.test","region":"cn"}'
```

The same `id` is not stored twice. `sitelens.purchase({ amount, sku, title, order_id })` still works.

## 4. Smallest GEO agent (5 min)

SiteLens does not log into the 15 answer UIs.

```bash
python -m sitelens.manage geo-agent --dry-run
```

With an OpenAI-compatible API:

```bash
export SITELENS_LLM_URL=https://api.openai.com/v1
export SITELENS_LLM_KEY=sk-...
python -m sitelens.manage geo-agent --base-url http://127.0.0.1:8788
```

Cron Mondays:

```
0 8 * * 1  python -m sitelens.manage geo-agent --base-url http://127.0.0.1:8788
```

See [geo-agent.md](geo-agent.md).

## 5. Daily alerts (5 min)

Set `alert_webhook` on the settings page. Once a day (UTC `alert_hour`) you get last-24h UV, orders, and GEO due/cited counts.

```bash
python -m sitelens.manage tick
curl -X POST http://127.0.0.1:8788/api/cron/tick -H "x-cron-token: slcron_..."
```

The Compose `tick` service hits this hourly.

Competitor traffic, ad spend, content calendars, and multi-tenant billing are out of scope.
