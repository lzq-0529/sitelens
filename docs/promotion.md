# Promotion & awesome-list submission pack (EN)

Copy-paste material for submitting SiteLens to lists and directories.
Chinese version: [promotion.zh-CN.md](promotion.zh-CN.md).
Do not submit anywhere that requires human attestation with bot text —
a maintainer should paste, read the target's rules, and submit in person.

## Pitches

**25 words**
> SiteLens is a self-hosted ops console for independent stores: traffic, SEO/AI crawlers, checkout conversion, and GEO citations for Shopify, WooCommerce, and CN+intl sites.

**One-liner for lists (≤ 120 chars)**
> Self-hosted store ops console: traffic, SEO crawlers, paid-order funnel, and AI-answer (GEO) citations. MIT, SQLite.

**160 chars**
> Self-hosted ops console for independent stores (Shopify/Woo/custom CN+intl). Traffic, Baidu/Google/AI crawlers, cart→paid funnel, and 15-engine GEO citation watch. MIT.

**Paragraph**
> SiteLens is the open-source console extracted from the production ops
> monitoring behind [qingjiaolab.com](https://qingjiaolab.com) (青椒智能脱敏,
> private document redaction before files go to AI). It watches an independent
> store end to end: who visited (Zhihu/小红书/Baidu/Google/UTM), whether search
> and AI crawlers (Googlebot, Baiduspider, GPTBot, Ahrefs…) actually came,
> who added to cart and paid (Shopify `orders/paid` / WooCommerce webhooks),
> and whether DeepSeek, 豆包, ChatGPT, Perplexity and 11 more answer engines
> cite the store this week. FastAPI + one SQLite file, owner/viewer accounts,
> no public signup. Screenshots in the repo are a demo store on purpose — no
> real site data is published.

## Where to submit, and when

| Target | Fit | Ready when | Notes |
| --- | --- | --- | --- |
| [oxnr/awesome-analytics](https://github.com/oxnr/awesome-analytics) | Website analytics / SEO | **Now** (fork + PR) | Entry below. Follow the file's existing format, one line, alphabetical where the section is alphabetical. |
| [awesome-selfhosted](https://github.com/awesome-selfhosted/awesome-selfhosted) (Analytics) | Self-hosted analytics | **After 2027-03-04** | Hard rule: first released > 4 months ago (v0.1.0 shipped 2026-11-04), actively maintained, working install docs, human-submitted. Submit via a YAML file in `awesome-selfhosted-data`, one project per PR. Calendar it; do not submit early. |
| [selfh.st/apps](https://selfh.st/apps-about/) | Self-hosted app directory | **Now** | Free, editorial review, daily refresh. Submit at selfh.st/submit (or hello@selfh.st) with repo, license, docs, screenshots. Ranking uses repo age/activity/stars, so keep committing. |
| [OpenAlternative](https://openalternative.co/submit) | “Open-source alternative to Google Analytics” | **Now** (free queue) | Needs a public repo, a named proprietary alternative, and a live website on a custom domain. Free listings wait in queue; paid skip-the-queue exists — do not pay yet. |
| [HelloGitHub](https://github.com/521xueweihan/HelloGitHub) | Chinese monthly open-source magazine | **Now** (self-recommend issue) | Submit via their issue template or hellogithub.com: title ≤ 50 chars, 32–256 char description, highlights, screenshots. New issue on the 28th monthly. |
| [bmpi-dev/awesome-seo](https://github.com/bmpi-dev/awesome-seo) | SEO tools (open-source preferred) | After English UI + some adoption | Curated, maturity matters. Link repo + MIT, describe crawler/landing scope neutrally, expect “too new” until there is usage evidence. |
| [awesome-privacy / privacy lists](https://github.com/pluja/awesome-privacy) | Self-hosted analytics alternative | English UI shipped — ready | Lead with self-hosting + no public signup; do not claim “cookie-free” — the tracker uses a localStorage visitor id, say so honestly. |
| AlternativeTo / OpenAlternative / SaaSHub | “Umami / Plausible / GA alternative” pages | Now (web forms) | Position as *store* alternative, not a GA clone. Add Shopify/Woo/GEO keywords. |
| Product Hunt | Launch audience | English UI shipped — after a hosted demo or 3-min demo video | Tagline below. Launching a Chinese-only UI to PH wastes the shot. |
| Hacker News (Show HN) | Dev/store operators | English UI shipped — ready | Title below. First comment must include stack, what it is not, and the demo login. |
| Reddit r/selfhosted, r/shopify, r/woocommerce | Operators | Now for feedback posts, not ads | “I extracted the store monitor from our production site, what is missing?” beats a launch post. Link the roadmap. |
| Indie Hackers / dev.to / Hashnode | Story traffic | Now | Angle: “We monitored qingjiaolab.com with an internal console; here is the open-source store slice.” Link qingjiaolab.com. |

## Ready-to-paste list entries

**awesome-analytics (Website analytics / SEO style):**
```markdown
* [SiteLens](https://github.com/lzq-0529/sitelens) - Self-hosted ops console for independent stores: traffic, search/AI crawlers, cart-to-paid-order funnel, and GEO citations across 15 answer engines (Shopify/WooCommerce/custom CN+intl). `MIT` `Self-Hosted` `Python`
```

**awesome-selfhosted YAML sketch (submit in awesome-selfhosted-data, follow their current template):**
```yaml
name: "SiteLens"
website_url: "https://github.com/lzq-0529/sitelens"
source_code_url: "https://github.com/lzq-0529/sitelens"
description: "Self-hosted ops console for independent stores: traffic, SEO/AI crawlers, checkout conversion, and GEO answer citations."
licenses:
  - MIT
platforms:
  - Docker
  - Python
tags:
  - Analytics
```

## Launch copy

**Show HN title**
> Show HN: SiteLens – self-hosted store ops (traffic, SEO crawlers, paid orders, GEO)

**Product Hunt tagline**
> Your store's traffic, crawlers, orders, and AI mentions — one private console

**First-comment skeleton (HN / Reddit / PH)**
> I run qingjiaolab.com (document redaction for AI). Our internal ops console
> watched the site, orders, search crawlers, and AI answers; I extracted the
> part any independent store can reuse and open-sourced it as SiteLens.
> Demo login is in the README (owner / sitelens-demo, mock store data).
> Honest gaps are listed in docs/roadmap.md — English UI and realtime are P0.
> Tell me what would block you from switching from Umami/Plausible.

## Rules we keep

- Screenshots and demo data stay mock (流明好物). Never publish qingjiaolab.com
  traffic, accounts, or orders.
- Link qingjiaolab.com as the production product behind the extraction, not
  as a public SiteLens demo (there is no public console for it).
- One project per PR, follow each list's template, no mass submissions in a day.

## Submitted log

Rule: submit via issues / web forms / email only. **No list forks are kept
under the maintainer account**; the profile shows only first-party projects.

| Date | Target | Method | Status |
| --- | --- | --- | --- |
| 2026-11-04 | HelloGitHub | [Issue #4245](https://github.com/521xueweihan/HelloGitHub/issues/4245) self-recommendation | Pending (monthly, out on the 28th) |
| 2026-11-04 | awesome-analytics | [Issue #306](https://github.com/oxnr/awesome-analytics/issues/306) suggestion, no fork | Pending |
| — | selfh.st/apps | Email hello@selfh.st | Needs the maintainer's own mailbox (copy above) |
| — | OpenAlternative | Sign-in required (magic link / GitHub OAuth) | Needs the maintainer to sign in |
| After 2027-03-04 | awesome-selfhosted | YAML PR (fork then, delete after merge) | Not yet eligible |
