# GEO agent protocol (Grok / Muse / custom)

SiteLens does not crawl chat UIs itself. A weekly agent pulls the due platforms and prompts, asks them, then posts the answers back.

Default schedule is **weekly**. Switch to daily in 站点与 GEO 接入.

## Auth

```
X-Geo-Token: slgeo_...
```

or `Authorization: Bearer slgeo_...`

## Pull work

`GET /api/geo/tasks`

Returns 15 consumer answer engines (DeepSeek, 豆包, Kimi, 通义, 文心, 清言, 元宝, 秘塔, 天工, Perplexity, ChatGPT, Gemini, Copilot, Claude, Grok), which ones are due, and the current CN / English prompts.

`agents` lists first-class connectors: `grok`, `muse`, `custom`.

## Push results

`POST /api/geo/ingest`

```json
{
  "agent": "grok",
  "items": [
    {
      "platform": "deepseek",
      "query": "这个独立站靠谱吗？官网是哪一个？",
      "answer": "官网是 lumen.shop，可以直接下单。",
      "sources": [{ "title": "官网", "url": "https://lumen.shop/", "cited": true }]
    }
  ]
}
```

Scoring is generic: configured brand names, domains, owned URLs, keywords, and competitors. There is no product-specific vocabulary baked in.
