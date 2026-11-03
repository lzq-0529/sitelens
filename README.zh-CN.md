<div align="center">

# SiteLens 独立站监控台

**给独立站用的流量、下单转化和 GEO 问答监测。**

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

[English](README.md) · 简体中文

</div>

独立站、公开官网想看流量、看国内外差、看搜索引擎有没有来抓、看 AI 问答有没有提到自己的店、看有没有人下单——可以自己跑这一套。后台不开放注册，默认不给搜索引擎收录。

转化看的是 **下单**，不是「立即体验」。漏斗是：

`浏览网站 → 看商品 → 加入购物车 → 开始结账 → 完成下单`

## 这五个页面

| 页面 | 做什么 |
| --- | --- |
| 流量与总览 | UV / PV、国内外对比、下单漏斗 |
| 国内外站点分析 | 访客明细、来源、爬虫、GEO 引用 |
| 网站用户与行为 | 已识别账号、加购 / 下单流水 |
| 订单与收入 | 已支付订单、退款、按商品看收入 |
| 后台账号与审计 | 管理员 / 只读、操作记录 |

另有「站点与 GEO 接入」：品牌、域名、竞品、采集脚本、Grok / Muse Token。

## GEO：每周交给 Grok 或 Muse

内置 15 家消费级问答平台。SiteLens 自己不去登录那些网页。Grok、Muse 或你自己的脚本：

1. `GET /api/geo/tasks` 拿走本周到期的平台和提问词
2. 去问
3. `POST /api/geo/ingest` 把回答和引用来源传回来

打分只用你配置的品牌名、域名、关键词、竞品，没有绑死某一家产品。默认每周，可改每天。协议见 [docs/geo-agent.md](docs/geo-agent.md)。

## 启动

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export SITELENS_DATA_DIR="$PWD/.local"
python -m sitelens.manage seed-demo
(cd web && npm ci && npm run build)
python -m sitelens
```

浏览器打开 http://127.0.0.1:8788 ，账号 `owner` / `sitelens-demo`。

只要空后台：

```bash
python -m sitelens.manage create-owner --username 你的名字
```

## 站点上的一段脚本

```html
<script defer src="http://127.0.0.1:8788/tracker.js" data-region="cn"></script>
```

海外站把 `data-region` 换成 `intl`。下单成功页：

```js
sitelens.purchase({ amount: 199, sku: "sku-1", title: "羊毛毯", order_id: "A1001" });
```

见 [docs/tracker.md](docs/tracker.md)。

## 刻意没放进来的

授权码、桌面端发版、设备管控、工作台试用——那些是某一家产品自己的运营，不是独立站通用能力。
