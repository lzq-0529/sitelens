# 推广与合集投递包（中文版）

把 SiteLens 投到清单、目录、社区时直接复制的材料。
English version: [promotion.md](promotion.md)。
凡是要求「本人提交」的合集，维护者要自己读规则、自己粘贴，不要用机器人代投。

## 介绍文案

**一句话**
> SiteLens 是给独立站的自托管运营监控台：流量、SEO/AI 爬虫、下单转化、GEO 引用，支持 Shopify、WooCommerce 和国内站+海外站。

**短介绍（列表用）**
> 独立站自托管运营监控：流量、百度/Google/AI 爬虫、加购到付款漏斗、15 家 AI 问答引用监测。MIT，一个 SQLite 文件。

**一段话**
> SiteLens 是从 [qingjiaolab.com](https://qingjiaolab.com)（青椒智能脱敏：文件交给 AI 前先私密脱敏）生产环境背后的运营监控里，提炼出来的开源版本。它把独立站运营要看的四件事放一个后台：谁来了（知乎/小红书/百度/Google/UTM）、搜索引擎和 AI 爬虫（Googlebot、Baiduspider、GPTBot、Ahrefs…）到底来没来、谁加了购谁付了款（Shopify `orders/paid` / WooCommerce webhook）、DeepSeek/豆包/ChatGPT/Perplexity 等 15 家问答这周有没有引用你的官网。FastAPI + 一个 SQLite，管理员/只读两档，不开放注册。仓库截图故意用演示店，不公布任何真实站点数据。

## 可以投哪里，什么时候投

| 渠道 | 适合的分类 | 什么时候 | 注意 |
| --- | --- | --- | --- |
| [oxnr/awesome-analytics](https://github.com/oxnr/awesome-analytics) | Website analytics / SEO | **现在**（Fork + PR） | 用下面现成条目，按文件现有格式一行一条。 |
| [awesome-selfhosted](https://github.com/awesome-selfhosted/awesome-selfhosted)（Analytics） | 自托管分析 | **首次发布满 4 个月后** | 硬规则：发布超 4 个月、持续维护、安装说明可用、真人提交。在 `awesome-selfhosted-data` 里交一个 YAML，一个 PR 只交一个项目。先记日历，不要提前投。 |
| [bmpi-dev/awesome-seo](https://github.com/bmpi-dev/awesome-seo) | SEO 工具（偏好开源） | 英文界面 + 有真实使用后 | 精选清单，看成熟度。描述保持中性，太新可能被拒，等有使用证据再投。 |
| awesome-privacy 类清单 | 自托管分析替代品 | 英文界面后 | 主打自托管 + 不开放注册；**不要写「无 Cookie」**——tracker 用 localStorage 存访客 id，要老实说。 |
| AlternativeTo / OpenAlternative / SaaSHub | Umami/Plausible/GA 替代品页 | 现在（网页表单） | 定位写「店铺运营替代」，不要写成 GA 克隆，带 Shopify/Woo/GEO 关键词。 |
| Product Hunt | 发布曝光 | 英文界面 + 在线演示或 3 分钟视频后 | 中文界面去打 PH 是浪费机会。 |
| Hacker News（Show HN） | 开发者/店主 | 英文界面后 | 标题见下。首评必须写清技术栈、不是什么、演示账号。 |
| Reddit r/selfhosted、r/shopify、r/woocommerce | 运营者 | 现在可发求反馈帖，别发广告帖 | 「我把生产站点的监控提炼开源了，还缺什么？」比发布帖有效，附路线图链接。 |
| V2EX、掘金、少数派、小众软件、HelloGitHub | 国内开发者/独立开发者 | 现在 | 角度：青椒官网背后的监控，怎么提炼成独立站能用的开源版。附 qingjiaolab.com 链接。HelloGitHub 在其官网/仓库按当期格式自荐。 |
| GitHubDaily 等推荐号 | GitHub 项目推荐 | 有英文界面和演示后 | 私信/投稿时给一句话介绍 + 演示账号 + 截图，不要只丢链接。 |

## 现成条目（直接粘贴）

**awesome-analytics 风格：**
```markdown
* [SiteLens](https://github.com/lzq-0529/sitelens) - Self-hosted ops console for independent stores: traffic, search/AI crawlers, cart-to-paid-order funnel, and GEO citations across 15 answer engines (Shopify/WooCommerce/custom CN+intl). `MIT` `Self-Hosted` `Python`
```

**awesome-selfhosted 的 YAML 草稿（到时按其最新模板交到 awesome-selfhosted-data）：**
```yaml
name: "SiteLens"
website_url: "https://github.com/lzq-0529/sitelens"
source_code_url: "https://github.com/lzq-0529/sitelens"
description: "Self-hosted ops console for independent stores: traffic, SEO crawlers, paid-order funnel, and AI-answer (GEO) citations."
licenses:
  - MIT
platforms:
  - Docker
  - Python
tags:
  - Analytics
```

## 发布文案

**Show HN 标题**
> Show HN: SiteLens – self-hosted store ops (traffic, SEO crawlers, paid orders, GEO)

**V2EX / 掘金标题参考**
> 把青椒官网背后的运营监控，提炼成独立站能用的开源后台了（流量/SEO/下单/GEO）

**首评骨架（HN / Reddit / V2EX 通用，先翻成对应语言）**
> 我是 qingjiaolab.com（青椒智能脱敏）的作者。我们内部运营台一直在看官网流量、订单、搜索引擎爬虫和 AI 问答引用，我把其中任何独立站都能复用的部分提炼出来开源，就是 SiteLens。README 里有演示账号（owner / sitelens-demo，演示店数据）。缺什么我都写在 docs/roadmap.zh-CN.md 里，英文界面和实时访客是 P0。欢迎告诉我：什么会阻止你从 Umami/Plausible 换过来？

## 守住的规矩

- 截图和演示数据一直用演示店（流明好物），绝不公布 qingjiaolab.com 的真实流量、账号、订单。
- 链接 qingjiaolab.com 时写清它是「提炼来源背后的生产产品」，不是 SiteLens 的公开演示（没有公开后台）。
- 一个 PR 只投一个项目，按各清单模板来，不要一天批量轰炸。
