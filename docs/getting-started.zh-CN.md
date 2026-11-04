# 30 分钟接入独立站

目标：你的店能在 SiteLens 里看到访客、识别用户、真实订单，并且 GEO / 日告警能自己跑。不新开页面。

## 0. 启动（5 分钟）

Docker：

```bash
cp .env.example .env
docker compose up -d --build
docker compose exec sitelens python -m sitelens.manage create-owner --username you --password '至少十位密码'
```

或本地：

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export SITELENS_DATA_DIR="$PWD/.local"
python -m sitelens.manage create-owner --username you
(cd web && npm ci && npm run build)
python -m sitelens
```

打开 http://127.0.0.1:8788 登录。演示数据：`python -m sitelens.manage seed-demo`（账号 `owner` / `sitelens-demo`）。

生产必须设 `SITELENS_ENV=production`，否则采集口可以不带 token。反代与 HTTPS 见 [deploy.md](deploy.md)。

## 1. 设置页：品牌和双域名（5 分钟）

打开「接入设置」：

1. 品牌名、别名、关键词
2. **国内站域名** `cn_hosts`、**海外站域名** `intl_hosts` 分行填写
3. 保存后复制采集脚本（含 `data-token`）

只填「官网域名」不够。没写 intl_hosts 时，海外站 host 会全部记成国内。

## SEO 不用另装站长工具

脚本贴上之后就会记。打开 **站点 / SEO / GEO**：

- 「搜索引擎与 AI 抓取」：百度、Google、GPTBot、Ahrefs、Semrush、DeepSeek 等有没有来，抓了哪些页
- 来源：知乎、小红书、微信、抖音、百度、Google，以及 `utm_source`
- 「爬虫日志」：路径、状态码、IP
- 页面上切「只看真人」，避免爬虫把转化率做假

不用再为了看收录单独开 Search Console / 站长平台。它们仍可作补充，日常运营看这一页就够。

## 2. 身份链路（5 分钟）

脚本会记 pageview。登录 / 注册成功后必须告诉 SiteLens 账号，否则「网站用户」是空的：

```html
<script defer src="https://sitelens.yourdomain.com/tracker.js" data-region="cn" data-token="slcol_..."></script>
<script>
  sitelens.identify(currentUser.email);
  // 或 sitelens.signup(currentUser.email);
</script>
```

后端会读顶层 `account` / `email`，也会读 `props.account`。tracker 现在两种都发。

## 3. 真实订单（5 分钟）

任选一条，不要只靠手工记账。

**Shopify**：后台通知 URL 填设置页里的 `/api/hooks/shopify`，密钥填 `shopify_secret`，主题用 `orders/paid`。

**WooCommerce**：订单 webhook 填 `/api/hooks/woocommerce`，密钥填 `woo_secret`。

**通用**：

```bash
curl -X POST https://sitelens.yourdomain.com/api/hooks/order \
  -H 'content-type: application/json' \
  -H "x-sitelens-token: slhook_..." \
  -d '{"id":"A1001","amount":199,"title":"羊毛毯","sku":"wool-1","customer":"ada@shop.test","region":"cn"}'
```

同一 `id` 不会重复入账。前端 `sitelens.purchase({ amount, sku, title, order_id })` 仍可用。

## 4. 最小 GEO Agent（5 分钟）

SiteLens 不会自己登录 15 家问答网页。先看本周要问什么：

```bash
python -m sitelens.manage geo-agent --dry-run
```

接 OpenAI 兼容接口后真正提问并回传：

```bash
export SITELENS_LLM_URL=https://api.openai.com/v1
export SITELENS_LLM_KEY=sk-...
python -m sitelens.manage geo-agent --base-url http://127.0.0.1:8788
```

crontab 每周一：

```
0 8 * * 1  cd /app && python -m sitelens.manage geo-agent --base-url http://127.0.0.1:8788
```

协议细节见 [geo-agent.md](geo-agent.md)。

## 5. 日告警（5 分钟）

设置页填告警 Webhook。每天（UTC `alert_hour`）推一次近 24 小时快照：

```json
{
  "type": "sitelens.daily",
  "visitors": 12,
  "orders": 3,
  "revenue_cents": 59700,
  "geo_due": 8,
  "geo_cited": 1
}
```

自己跑：

```bash
python -m sitelens.manage tick
# 或
curl -X POST http://127.0.0.1:8788/api/cron/tick -H "x-cron-token: slcron_..."
```

Docker Compose 里的 `tick` 服务每小时打一次。

到这里六页后台就能接真站。竞品流量、广告花费、内容日历、多租户计费都不在范围内。
