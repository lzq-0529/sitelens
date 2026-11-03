<div align="center">

# SiteLens

**Traffic, order conversion, and GEO answer monitoring for independent websites.**

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776ab.svg)
![React](https://img.shields.io/badge/ui-Ant%20Design%20Pro-1677ff.svg)

[简体中文](README.zh-CN.md) · English

</div>

SiteLens is a small private console you run yourself. It is for people who operate an independent storefront (Shopify, WooCommerce, a custom site, a CN + international pair of sites) and want four things in one place:

1. **Traffic & overview** — UV / PV, sources, landing pages, CN vs international
2. **Site analysis** — visitors, search-engine / AI crawlers, GEO citations
3. **Visitors & behavior** — identified accounts, add-to-cart, checkout, purchase
4. **Orders & revenue** — paid orders, refunds, revenue by product
5. **Admin & audit** — owner / viewer accounts, no public signup

Conversion is **order**, not “try it now”. The funnel is:

`visit → view product → add to cart → checkout → order`

## GEO (Grok / Muse)

Fifteen consumer answer engines are built in (DeepSeek, 豆包, Kimi, 通义, 文心, 清言, 元宝, 秘塔, 天工, Perplexity, ChatGPT, Gemini, Copilot, Claude, Grok).

SiteLens does not log into those products. A weekly agent — Grok, Muse, or anything you write — pulls due prompts from `GET /api/geo/tasks` and posts answers to `POST /api/geo/ingest`. Scoring uses **your** brand, domains, keywords, and competitors.

See [docs/geo-agent.md](docs/geo-agent.md).

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export SITELENS_DATA_DIR="$PWD/.local"
python -m sitelens.manage seed-demo          # owner / sitelens-demo + sample store data
(cd web && npm ci && npm run build)
python -m sitelens                           # http://127.0.0.1:8788
```

Or create an empty owner and skip demo data:

```bash
python -m sitelens.manage create-owner --username you
```

## Drop-in tracker

```html
<script defer src="http://127.0.0.1:8788/tracker.js" data-region="cn"></script>
```

```js
sitelens.addToCart("sku-1", "Wool throw");
sitelens.purchase({ amount: 199, sku: "sku-1", title: "Wool throw" });
```

Details: [docs/tracker.md](docs/tracker.md).

## What this is not

This is not a license manager, desktop updater, or any one vendor’s ops console. Qingjiao-specific modules (activation codes, releases, device control, “try the workbench”) were left out on purpose.

## Tests

```bash
python -m unittest discover -s tests
```
