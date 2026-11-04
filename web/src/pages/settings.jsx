import { CheckCircleFilled, CopyOutlined, LinkOutlined, ReloadOutlined, WarningFilled } from "@ant-design/icons";
import { PageContainer, ProCard } from "@ant-design/pro-components";
import { App, Button, Col, Form, Input, InputNumber, Radio, Row, Space, Tabs, Tag, Typography } from "antd";
import { api } from "../api";
import { useAuth } from "../auth";
import { Kpis, LoadError, useLoad } from "../components";

const lines = (value) => (Array.isArray(value) ? value.join("\n") : value || "");
const countLines = (value) => (Array.isArray(value) ? value.filter(Boolean).length : 0);

function mint(prefix) {
  const bytes = new Uint8Array(18);
  crypto.getRandomValues(bytes);
  const raw = btoa(String.fromCharCode(...bytes)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
  return `${prefix}${raw}`;
}

function CodeBlock({ title, text, hint }) {
  const { message } = App.useApp();
  return (
    <div className="sl-code-panel">
      <div className="sl-code-panel-head">
        <span>{title}</span>
        <Button
          size="small"
          icon={<CopyOutlined />}
          onClick={async () => {
            await navigator.clipboard.writeText(text);
            message.success("已复制");
          }}
        >
          复制
        </Button>
      </div>
      <pre className="sl-code-block">{text}</pre>
      {hint ? <div className="sl-code-panel-hint">{hint}</div> : null}
    </div>
  );
}

function EndpointCard({ title, badge, url, extra, children }) {
  const { message } = App.useApp();
  return (
    <div className="sl-hook-card">
      <div className="sl-hook-card-head">
        <strong>{title}</strong>
        {badge ? <Tag color="green">{badge}</Tag> : <Tag>待配置</Tag>}
      </div>
      <div className="sl-hook-url">
        <LinkOutlined />
        <Typography.Text ellipsis={{ tooltip: url }}>{url}</Typography.Text>
        <Button
          type="link"
          size="small"
          icon={<CopyOutlined />}
          onClick={async () => {
            await navigator.clipboard.writeText(url);
            message.success("已复制地址");
          }}
        >
          复制
        </Button>
      </div>
      {extra ? <p className="sl-hook-extra">{extra}</p> : null}
      {children}
    </div>
  );
}

export function SettingsPage() {
  const { isOwner } = useAuth();
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const settings = useLoad(() => api("/api/admin/settings"), []);
  const data = settings.data || {};
  const origin = typeof window !== "undefined" ? window.location.origin : "http://127.0.0.1:8788";
  const token = data.collect_token || "";
  const tokenAttr = token ? ` data-token="${token}"` : "";
  const snippetCn = `<script defer src="${origin}/tracker.js" data-region="cn"${tokenAttr}></script>`;
  const snippetIntl = `<script defer src="${origin}/tracker.js" data-region="intl"${tokenAttr}></script>`;
  const identifySample = `sitelens.identify(user.email);
sitelens.signup(user.email);
sitelens.addToCart("sku-1", "亚麻床品四件套");
sitelens.purchase({ amount: 199, sku: "sku-1", title: "亚麻床品四件套", order_id: "A1001" });`;
  const hooks = data.hooks || {};
  const shopifyReady = Boolean(data.shopify_secret);
  const wooReady = Boolean(data.woo_secret);
  const genericReady = Boolean(data.hook_token);
  const orderReady = shopifyReady || wooReady || genericReady;

  const save = async (values) => {
    try {
      await api("/api/admin/settings", { method: "PUT", body: values });
      message.success("设置已保存，脚本和 webhook 立即生效");
      settings.reload();
    } catch (exc) {
      message.error(exc.message);
    }
  };

  return (
    <PageContainer
      subTitle="把独立站接进监控台：采集脚本、国内外域名、订单 webhook、SEO / GEO 关键词、日告警。"
      extra={
        isOwner ? (
          <Button type="primary" onClick={() => form.submit()} disabled={settings.loading}>
            保存全部设置
          </Button>
        ) : (
          <Tag>只读账号不能改接入</Tag>
        )
      }
    >
      <LoadError error={settings.error} />
      <Kpis
        loading={settings.loading}
        cols={6}
        items={[
          { title: "采集密钥", value: token ? "已配置" : "未配置", badge: token ? "data-token" : "生产会拒收", hint: token ? `${token.slice(0, 12)}…` : "设置页生成后贴到站点", color: token ? "#16a34a" : "#f59e0b" },
          { title: "国内域名", value: countLines(data.cn_hosts), badge: "cn_hosts", hint: "匹配到这些 host 记为国内", color: "#2563eb" },
          { title: "海外域名", value: countLines(data.intl_hosts), badge: "intl_hosts", hint: "没填则海外站会算成国内", color: "#7c3aed" },
          { title: "订单接入", value: orderReady ? "已接通" : "未接通", badge: [shopifyReady && "Shopify", wooReady && "Woo", genericReady && "通用"].filter(Boolean).join(" · ") || "webhook", hint: "Shopify / Woo / 通用三选一", color: orderReady ? "#0ea5e9" : "#f59e0b" },
          { title: "日告警", value: data.alert_webhook ? "已配置" : "未配置", badge: `UTC ${data.alert_hour ?? 1} 点`, hint: data.alert_webhook || "填 Webhook 或跑 cron/tick", color: data.alert_webhook ? "#16a34a" : "#64748b" },
          { title: "GEO 节奏", value: data.geo_schedule === "daily" ? "每天" : "每周", badge: data.ingest_token ? "Agent 可用" : "登录后可见", hint: "15 家问答平台巡检", color: "#ec4899" },
        ]}
      />
      <Form
        form={form}
        layout="vertical"
        disabled={!isOwner}
        initialValues={{
          ...data,
          brand_aliases: lines(data.brand_aliases),
          domains: lines(data.domains),
          cn_hosts: lines(data.cn_hosts),
          intl_hosts: lines(data.intl_hosts),
          keywords: lines(data.keywords),
          competitors: lines(data.competitors),
          owned_urls: lines(data.owned_urls),
        }}
        key={`${data.brand}-${data.collect_token}-${data.hook_token}-${data.alert_webhook}`}
        onFinish={save}
      >
        <ProCard bordered bodyStyle={{ paddingTop: 8 }} loading={settings.loading}>
          <Tabs
            items={[
              { key: "tracker", label: "1. 采集脚本", children: <TrackerPane snippetCn={snippetCn} snippetIntl={snippetIntl} identifySample={identifySample} token={token} form={form} isOwner={isOwner} /> },
              { key: "site", label: "2. 站点档案", children: <ProfilePane /> },
              { key: "orders", label: "3. 订单接入", children: <OrdersPane hooks={hooks} origin={origin} shopifyReady={shopifyReady} wooReady={wooReady} genericReady={genericReady} form={form} isOwner={isOwner} /> },
              { key: "alerts", label: "4. 告警与 GEO", children: <AlertsPane data={data} hooks={hooks} origin={origin} /> },
            ]}
          />
        </ProCard>
      </Form>
    </PageContainer>
  );
}

function TrackerPane({ snippetCn, snippetIntl, identifySample, token, form, isOwner }) {
  return (
    <Space direction="vertical" size={16} style={{ width: "100%" }}>
      <div className="sl-setup-steps">
        <div className="sl-setup-step">
          <span>01</span>
          <strong>贴脚本</strong>
          <p>国内站 / 海外站各贴一段，生产必须带 token。</p>
        </div>
        <div className="sl-setup-step">
          <span>02</span>
          <strong>认人</strong>
          <p>登录后调用 identify，否则「网站用户」是空的。</p>
        </div>
        <div className="sl-setup-step">
          <span>03</span>
          <strong>收单</strong>
          <p>purchase() 或 Shopify / Woo webhook，只记已支付。</p>
        </div>
        <div className="sl-setup-step">
          <span>04</span>
          <strong>SEO / GEO</strong>
          <p>爬虫自动记。问答平台按第 4 步的节奏巡检。</p>
        </div>
      </div>
      <Row gutter={[16, 16]}>
        <Col xs={24} xl={14}>
          <CodeBlock title="国内站脚本" text={snippetCn} hint="放在 </body> 前。生产环境不带 data-token 会被拒收。" />
        </Col>
        <Col xs={24} xl={10}>
          <CodeBlock title="海外站脚本" text={snippetIntl} hint="只改 data-region=intl，域名填到 intl_hosts。" />
        </Col>
      </Row>
      <Row gutter={[16, 16]}>
        <Col xs={24} xl={14}>
          <CodeBlock title="认人与下单" text={identifySample} hint="identify / signup 的邮箱会出现在「网站用户」。订单更推荐走 webhook。" />
        </Col>
        <Col xs={24} xl={10}>
          <div className="sl-setup-note">
            <div className="sl-setup-note-title">
              {token ? <CheckCircleFilled style={{ color: "#16a34a" }} /> : <WarningFilled style={{ color: "#f59e0b" }} />}
              采集密钥
            </div>
            <p>tracker 的 data-token。保存后上面的脚本会带上它。</p>
            <Space.Compact style={{ width: "100%" }}>
              <Form.Item name="collect_token" noStyle>
                <Input placeholder="slcol_..." />
              </Form.Item>
              {isOwner && (
                <Button icon={<ReloadOutlined />} onClick={() => form.setFieldValue("collect_token", mint("slcol_"))}>
                  生成
                </Button>
              )}
            </Space.Compact>
          </div>
        </Col>
      </Row>
    </Space>
  );
}

function ProfilePane() {
  return (
    <Row gutter={[20, 8]}>
      <Col xs={24} lg={12}>
        <Form.Item name="brand" label="品牌名" rules={[{ required: true, message: "GEO 打分要用品牌名" }]}>
          <Input placeholder="流明好物" />
        </Form.Item>
        <Form.Item name="category" label="品类">
          <Input placeholder="家居、服饰、保健品" />
        </Form.Item>
        <Form.Item name="brand_aliases" label="品牌别名" extra="每行一个。AI 回答里出现这些也算提及。">
          <Input.TextArea rows={3} placeholder={"Lumen Goods\nlumen.shop"} />
        </Form.Item>
        <Form.Item name="keywords" label="希望被提到的关键词" extra="SEO / GEO 打分用，不是广告关键词。">
          <Input.TextArea rows={3} placeholder={"独立站\n亚麻床品"} />
        </Form.Item>
        <Form.Item name="competitors" label="竞品名">
          <Input.TextArea rows={2} placeholder="每行一个" />
        </Form.Item>
      </Col>
      <Col xs={24} lg={12}>
        <Form.Item name="domains" label="官网域名" extra="用于 GEO 判断「引用了你的官网」。">
          <Input.TextArea rows={2} placeholder={"lumen.shop\nwww.lumen.shop"} />
        </Form.Item>
        <Form.Item
          name="cn_hosts"
          label="国内站 host"
          extra="流量区域看这个，不要只填官网域名。匹配到的记为国内。"
        >
          <Input.TextArea rows={3} placeholder={"lumen.shop\nwww.lumen.shop"} />
        </Form.Item>
        <Form.Item name="intl_hosts" label="海外站 host" extra="没写海外 host 时，国际域名会全部算成国内。">
          <Input.TextArea rows={3} placeholder={"intl.lumen.shop\nwww.lumengoods.com"} />
        </Form.Item>
        <Form.Item name="owned_urls" label="自有内容 URL" extra="GEO 判断「直接引用了你的内容」时用。">
          <Input.TextArea rows={3} placeholder="https://lumen.shop/journal/linen" />
        </Form.Item>
      </Col>
    </Row>
  );
}

function OrdersPane({ hooks, origin, shopifyReady, wooReady, genericReady, form, isOwner }) {
  return (
    <Space direction="vertical" size={16} style={{ width: "100%" }}>
      <div className="sl-hook-grid">
        <EndpointCard
          title="Shopify"
          badge={shopifyReady ? "密钥已填" : ""}
          url={hooks.shopify || `${origin}/api/hooks/shopify`}
          extra="后台 → 通知 → 创建 webhook。事件选 orders/paid。密钥填到下面。"
        />
        <EndpointCard
          title="WooCommerce"
          badge={wooReady ? "密钥已填" : ""}
          url={hooks.woocommerce || `${origin}/api/hooks/woocommerce`}
          extra="Woo 设置 → 高级 → Webhook。主题选 Order paid / updated。"
        />
        <EndpointCard
          title="通用 JSON"
          badge={genericReady ? "密钥已填" : ""}
          url={hooks.order || `${origin}/api/hooks/order`}
          extra="请求头 X-Sitelens-Token。同一订单 id 不会重复入账。"
        />
      </div>
      <Row gutter={[20, 8]}>
        <Col xs={24} lg={12}>
          <Form.Item name="shopify_secret" label="Shopify webhook secret" extra="校验 X-Shopify-Hmac-Sha256">
            <Input.Password placeholder="从 Shopify 通知页复制" />
          </Form.Item>
          <Form.Item name="woo_secret" label="WooCommerce webhook secret" extra="校验 X-WC-Webhook-Signature">
            <Input.Password placeholder="从 Woo webhook 页复制" />
          </Form.Item>
        </Col>
        <Col xs={24} lg={12}>
          <Form.Item label="通用订单密钥" extra="自建站或中台推单用。">
            <Space.Compact style={{ width: "100%" }}>
              <Form.Item name="hook_token" noStyle>
                <Input.Password placeholder="slhook_..." />
              </Form.Item>
              {isOwner && (
                <Button icon={<ReloadOutlined />} onClick={() => form.setFieldValue("hook_token", mint("slhook_"))}>
                  生成
                </Button>
              )}
            </Space.Compact>
          </Form.Item>
          <CodeBlock
            title="通用订单示例"
            text={`curl -X POST ${origin}/api/hooks/order \\\n  -H 'content-type: application/json' \\\n  -H "x-sitelens-token: slhook_..." \\\n  -d '{"id":"A1001","amount":199,"title":"亚麻床品","sku":"linen-1","customer":"ada@shop.test","region":"cn"}'`}
          />
        </Col>
      </Row>
    </Space>
  );
}

function AlertsPane({ data, hooks, origin }) {
  return (
    <Row gutter={[20, 16]}>
      <Col xs={24} lg={12}>
        <Form.Item name="geo_schedule" label="GEO 巡检节奏" extra="只决定任务是否到期，不会自己去登录问答网站。">
          <Radio.Group optionType="button" options={[{ value: "weekly", label: "每周（推荐）" }, { value: "daily", label: "每天" }]} />
        </Form.Item>
        <Form.Item name="alert_webhook" label="日告警 Webhook URL" extra="每天推近 24 小时 UV、已支付订单、GEO 到期数。">
          <Input placeholder="https://hooks.example/sitelens" />
        </Form.Item>
        <Form.Item name="alert_hour" label="日告警小时（UTC）">
          <InputNumber min={0} max={23} style={{ width: 160 }} />
        </Form.Item>
      </Col>
      <Col xs={24} lg={12}>
        <div className="sl-setup-note">
          <div className="sl-setup-note-title">Grok / Muse / 最小 Agent</div>
          {data.ingest_token ? (
            <Typography.Paragraph copyable={{ text: data.ingest_token }} style={{ marginBottom: 8 }}>
              GEO Token　<code>{data.ingest_token}</code>
            </Typography.Paragraph>
          ) : (
            <p>管理员登录后可见 Token。</p>
          )}
          <p>
            <code>python -m sitelens.manage geo-agent --dry-run</code> 拉本周到期平台。真正提问需要{" "}
            <code>SITELENS_LLM_URL</code>。
          </p>
          {data.cron_token && (
            <Typography.Paragraph copyable={{ text: data.cron_token }} style={{ marginBottom: 8 }}>
              Cron Token　<code>{data.cron_token}</code>
            </Typography.Paragraph>
          )}
          <CodeBlock title="日告警 / tick" text={`curl -X POST ${hooks.cron || `${origin}/api/cron/tick`} \\\n  -H "x-cron-token: slcron_..."`} />
        </div>
      </Col>
    </Row>
  );
}
