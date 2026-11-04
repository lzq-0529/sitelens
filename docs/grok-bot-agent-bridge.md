# Grok Bot · 总调度专家 — 外部 Agent 互通协议

长久文档（协议说明）。与 **Grok Bot · 总调度专家**（Ziqi Liu 的主 bot）双向通信、投递正文与文件时，按本文执行。

- 文档用途：协议与字段约定（可公开给外部 Agent）
- 通信入口：下方 Webhook（**长久有效**，除非例程被删）
- 密钥：只由人类操作者私下发给你，**不要**写进公开仓库或聊天记录

---

## 1. 你是谁 / 对方是谁

| 角色 | 说明 |
|------|------|
| 对方 | Grok Bot · 总调度专家（Cursor / Grok Bot 主调度） |
| 你 | 任意外部 Agent（Cursor Cloud、其他 IDE Agent、自建服务等） |
| 人类 | Ziqi；对方收到有效消息后会用中文转告 Ziqi |

---

## 2. 长久入口（Webhook）

由人类操作者填入（在 Grok Bot → 本 bot 信息页 → 例程「外部Agent互通」里复制）：

```
WEBHOOK_URL=<<PASTE_WEBHOOK_URL>>
Authorization: <<PASTE_AUTHORIZATION_HEADER>>
```

- `WEBHOOK_URL`：POST 目标，HTTPS，长期不变
- `Authorization`：例程面板里的 Authorization header 整行（或按面板说明带 Bearer / 自定义头）
- **不要**把 Key 写进本协议的公开副本；拿到后存进你自己的 secret 存储

### 最小请求

```http
POST {WEBHOOK_URL}
Content-Type: application/json
Authorization: {从操作者拿到的值}

{
  "from": "your-agent-name",
  "message": "一句话说明你要对方做什么或告知什么",
  "reply_to": "https://your.example/callback"
}
```

对方收到后会：

1. 把摘要（和文件）告诉 Ziqi  
2. 若你提供了 `reply_to` / `callback_url`，向该地址 POST 一份确认 JSON（见第 4 节）

---

## 3. 载荷字段

| 字段 | 必填 | 说明 |
|------|------|------|
| `from` | 是 | 你的稳定标识（agent 名 / 项目名） |
| `message` | 是 | 给对方看的说明（中英文均可；对方会用中文转告 Ziqi） |
| `message_id` | 否 | 幂等/对账用；建议 UUID |
| `reply_to` 或 `callback_url` | 强烈建议 | 你的 HTTPS 回调；对方用它回你，实现双向沟通 |
| `content` | 否 | 长文正文（协议、报告、草稿等） |
| `files` | 否 | 文件列表，见下 |
| `notify_ziqi` | 否 | 默认 `true`；仅调试可设 `false`（仍可能被记录） |
| `meta` | 否 | 任意 JSON，便于你侧路由 |

### 文件 `files[]`

每项二选一：

```json
{
  "name": "report.pdf",
  "url": "https://…可公开或带时效下载的 HTTPS…"
}
```

或（小文件，建议 &lt; 2MB）：

```json
{
  "name": "notes.md",
  "content_base64": "..."
}
```

对方会把文件落到自己的工作区，并在回传与给 Ziqi 的汇报里带上本地路径。

### 完整示例

```json
{
  "from": "cursor-cloud-agent-sitelens",
  "message_id": "9b2f0c1a-…. ",
  "message": "已生成 sitelens 部署检查清单，请转交 Ziqi 并确认是否开 PR。",
  "reply_to": "https://your-agent.example/hooks/grok-bot-reply",
  "content": "## 检查清单\n- …",
  "files": [
    {
      "name": "checklist.md",
      "url": "https://…/checklist.md"
    }
  ],
  "meta": { "repo": "lzq-0529/sitelens", "priority": "normal" }
}
```

---

## 4. 对方如何回你（双向）

若请求里有 `reply_to` 或 `callback_url`，对方会 POST：

```json
{
  "ok": true,
  "received_at": "2026-11-04 15:30:00 CST",
  "from": "Grok Bot · 总调度专家",
  "in_reply_to": "你的 message_id 或空",
  "summary": "已收到并已转告 Ziqi",
  "saved_files": ["/workspace/external-agent-inbox/…/checklist.md"],
  "reply": "可选：对方的补充说明或后续问题"
}
```

你侧应：

1. 暴露稳定的 HTTPS `reply_to`（不要用会几小时就失效的隧道，除非你会更新协议里的地址）  
2. 校验来源（共享 secret、IP allowlist 或仅内网）由你自行决定；本协议不强制  
3. 若还要继续对话：再向 Webhook POST 一条，带上同一 `message_id` 或引用上次 id  

---

## 5. 安全与边界

- Webhook Key / Authorization **只**经人类通道下发  
- 不要在载荷里塞密码、银行卡、私钥；需要凭证时说明「请 Ziqi 在 Vault 里授权」，不要明文传  
- 对方不会执行未经验证的破坏性指令；需要改生产/删已发内容时会升级 Ziqi  
- 本入口 **不是** 青椒外部调度派单通道（那是另一条例程）；请勿把 commander 派单 JSON 发到这里  

---

## 6. 人类操作者检查清单（Ziqi）

1. 打开本 bot → 例程「外部Agent互通」  
2. 复制 [Webhook URL]、[Webhook key] / [Authorization header]  
3. 把 URL 与 Authorization **私下**发给外部 Agent（或写入对方 secret），**不要**提交进公开 git  
4. 把本协议链接发给外部 Agent 当说明文档  
5. 外部 Agent 试发一条带 `reply_to` 的 ping；你应在本聊天看到汇报，对方应收到 callback  

---

## 7. 版本

- protocol_id: `grok-bot-agent-bridge-v1`  
- created: 2026-11-04 (Asia/Shanghai)  
- owner_bot: Grok Bot · 总调度专家  
- routine: 外部Agent互通  

