# SiteLens vs. the field — honest gaps and roadmap

SiteLens is not trying to be GA4, Matomo, PostHog, and Uptime Kuma at once.
This page says what the neighbours do better today, what we will build next,
and what we will deliberately not build. Updated 2026-11-04.

## Where SiteLens already differs

| | Umami / Plausible | Matomo | PostHog | Uptime Kuma | **SiteLens** |
| --- | --- | --- | --- | --- | --- |
| Best at | Pageviews, referrers, simple goals | GA-style depth, segments, ecommerce | Product events, replay, flags, A/B | “Is it up?”, SSL, status pages | **Store ops for CN + intl independents** |
| Store funnel → paid order | Goal-level | Yes, heavy | DIY events | No | **visit → product → cart → checkout → paid, built in** |
| China sources (知乎/小红书/百度…) | Generic referrer | Generic referrer | DIY | No | **Named out of the box** |
| Search + AI crawlers (Baidu/Google/GPTBot…) | Bot-filtered away | Partial | No | No | **First-class SEO tab + crawl log** |
| AI answer citations (GEO) | No | No | No | No | **15 engines, incl. DeepSeek/豆包/Kimi** |
| CN + intl hosts split | Multi-site, not region semantics | Segments | DIY | No | **`cn_hosts` / `intl_hosts` semantics** |
| Stack to run | Node + Postgres (Umami) / ClickHouse (Plausible CE) | PHP + MySQL | Many services | Node + SQLite | **FastAPI + one SQLite file** |

Positioning in one line: *Umami tells you traffic happened. SiteLens tells a
store operator whether that traffic came from search/AI, and whether it paid.*

## P0 — next, blocks adoption

These are the gaps a stranger hits in the first week. Rough order:

1. ~~**English UI (i18n toggle).**~~ **Shipped**: a 中文/EN toggle in the
   console header; English screenshots are in the English README. Long-tail
   strings keep being filled in.
2. ~~**Realtime.**~~ **Shipped**: a live strip on Overview (visitors / views /
   carts / orders in the last 30 min, current page, top source). A dedicated
   realtime page with a live feed is still open.
3. **Multi-store.** One install, several stores/brands, site switcher. Today
   one SiteLens = one CN+intl pair. Agencies and two-brand operators are stuck.
4. **Campaign attribution.** Break down `utm_medium` / `utm_campaign` / `utm_term`
   (today only source is named) and tie landing → cart → paid order per
   campaign and per SKU, so ad/content spend has a denominator.
5. **Export, retention, backup.** CSV/API export of visitors/orders/crawls,
   configurable data-retention pruning, documented SQLite backup/restore.
   Self-hosters will not trust a black box with their only copy.
6. **Alert channels + anomaly.** Daily webhook exists. Add Slack / Telegram /
   飞书 / 企业微信 / email, plus “traffic dropped / no paid order in N hours /
   crawler stopped coming” instead of only a fixed daily push.
7. **Uptime + SSL mini-check.** Not an Uptime Kuma clone: one HTTP check per
   configured host, cert-expiry days, down/recovered alert through the same
   webhook. “网站监控” buyers search for this word; today we have none of it.

## P1 — depth store operators ask for second

- **Journey & retention:** visitor path (landing → product → cart), new vs
  returning, bounce / time-on-site. Device/browser/OS data is already stored;
  surface it fully (country/city only with an offline GeoIP file, no cloud lookup).
- **Ecommerce depth:** ~~AOV, repeat buyers~~ **shipped**; abandoned-checkout
  KPI **shipped** (the named list is open). Still open: product conversion rate
  (view → paid per SKU) and revenue by channel/coupon.
- **SEO depth:** Google Search Console + 百度站长 data import next to crawl
  logs, 404/broken-path report from crawl status, sitemap/robots health check,
  optional keyword rank snapshots. Core Web Vitals (LCP/CLS/INP) via tracker.
- **GEO depth:** ~~visibility score + competitor share of voice~~ **shipped**
  (score, SoV %, competitor mention tags). Still open: SoV trend over time,
  per-prompt history, sentiment, more one-click agent providers.
- **One-click install:** Shopify app/theme snippet and a WooCommerce plugin,
  instead of “paste this script + configure a webhook by hand”.
- **Sharing:** read-only share link for a dashboard, scheduled weekly report
  (email/webhook PDF or image) for a boss/partner.

## P2 — deliberately not building

- Heatmaps / session replay — heavy, privacy-hostile, PostHog/Matomo territory.
- Feature flags / A-B testing — product-analytics job, not store ops.
- Ad-spend sync (Google/Meta Ads cost import) — attribution beyond UTM belongs
  in the ad platforms until P0 campaign reporting exists.
- Multi-tenant SaaS billing / hosted cloud — SiteLens stays a thing you run.
- Full log analytics / APM / server metrics — pair with Uptime Kuma, Netdata,
  or GoAccess instead of reimplementing them.

## How to influence this list

Open an issue with your store shape (Shopify/Woo/custom, CN/intl, monthly
orders). “I could not switch from Umami because ___” is the most useful
sentence you can send us.
