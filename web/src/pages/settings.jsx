import { CheckCircleFilled, CopyOutlined, LinkOutlined, ReloadOutlined, WarningFilled } from "@ant-design/icons";
import { PageContainer, ProCard } from "@ant-design/pro-components";
import { App, Button, Col, Form, Input, InputNumber, Radio, Row, Space, Tabs, Tag, Typography } from "antd";
import { api } from "../api";
import { useAuth } from "../auth";
import { Kpis, LoadError, useLoad } from "../components";
import { useLang, useT } from "../i18n";

const lines = (value) => (Array.isArray(value) ? value.join("\n") : value || "");
const countLines = (value) => (Array.isArray(value) ? value.filter(Boolean).length : 0);

function mint(prefix) {
  const bytes = new Uint8Array(18);
  crypto.getRandomValues(bytes);
  const raw = btoa(String.fromCharCode(...bytes)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
  return `${prefix}${raw}`;
}

function CodeBlock({ title, text, hint }) {
  const t = useT();
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
            message.success(t("已复制", "Copied"));
          }}
        >
          {t("复制", "Copy")}
        </Button>
      </div>
      <pre className="sl-code-block">{text}</pre>
      {hint ? <div className="sl-code-panel-hint">{hint}</div> : null}
    </div>
  );
}

function EndpointCard({ title, badge, url, extra, children }) {
  const t = useT();
  const { message } = App.useApp();
  return (
    <div className="sl-hook-card">
      <div className="sl-hook-card-head">
        <strong>{title}</strong>
        {badge ? <Tag color="green">{badge}</Tag> : <Tag>{t("待配置", "Not set")}</Tag>}
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
            message.success(t("已复制地址", "Copied"));
          }}
        >
          {t("复制", "Copy")}
        </Button>
      </div>
      {extra ? <p className="sl-hook-extra">{extra}</p> : null}
      {children}
    </div>
  );
}

export function SettingsPage() {
  const t = useT();
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
  const { isEn } = useLang();
  const sampleTitle = isEn ? "Linen bedding set" : "亚麻床品四件套";
  const identifySample = `sitelens.identify(user.email);
sitelens.signup(user.email);
sitelens.addToCart("sku-1", "${sampleTitle}");
sitelens.purchase({ amount: 199, sku: "sku-1", title: "${sampleTitle}", order_id: "A1001" });`;
  const hooks = data.hooks || {};
  const shopifyReady = Boolean(data.shopify_secret);
  const wooReady = Boolean(data.woo_secret);
  const genericReady = Boolean(data.hook_token);
  const orderReady = shopifyReady || wooReady || genericReady;

  const save = async (values) => {
    try {
      await api("/api/admin/settings", { method: "PUT", body: values });
      message.success(t("设置已保存，脚本和 webhook 立即生效", "Saved. Tracker and webhooks are live."));
      settings.reload();
    } catch (exc) {
      message.error(exc.message);
    }
  };

  return (
    <PageContainer
      subTitle={t("把独立站接进监控台：采集脚本、国内外域名、订单 webhook、SEO / GEO 关键词、日告警。", "Connect your store: tracker, CN/intl hosts, order webhooks, SEO/GEO keywords, daily alerts.")}
      extra={
        isOwner ? (
          <Button type="primary" onClick={() => form.submit()} disabled={settings.loading}>
            {t("保存全部设置", "Save all settings")}
          </Button>
        ) : (
          <Tag>{t("只读账号不能改接入", "Viewers cannot edit setup")}</Tag>
        )
      }
    >
      <LoadError error={settings.error} />
      <Kpis
        loading={settings.loading}
        cols={6}
        items={[
          { title: t("采集密钥", "Collect token"), value: token ? t("已配置", "Set") : t("未配置", "Missing"), badge: token ? "data-token" : t("生产会拒收", "Required in prod"), hint: token ? `${token.slice(0, 12)}…` : t("生成后贴到站点", "Generate, then paste"), color: token ? "#16a34a" : "#f59e0b" },
          { title: t("国内域名", "China hosts"), value: countLines(data.cn_hosts), badge: "cn_hosts", hint: t("匹配到这些 host 记为国内", "These hosts count as China"), color: "#2563eb" },
          { title: t("海外域名", "Intl hosts"), value: countLines(data.intl_hosts), badge: "intl_hosts", hint: t("没填则海外站会算成国内", "Empty = overseas counts as China"), color: "#7c3aed" },
          { title: t("订单接入", "Order ingest"), value: orderReady ? t("已接通", "Connected") : t("未接通", "Not connected"), badge: [shopifyReady && "Shopify", wooReady && "Woo", genericReady && t("通用", "Generic")].filter(Boolean).join(" · ") || "webhook", hint: t("Shopify / Woo / 通用三选一", "Pick Shopify / Woo / generic"), color: orderReady ? "#0ea5e9" : "#f59e0b" },
          { title: t("日告警", "Daily alert"), value: data.alert_webhook ? t("已配置", "Set") : t("未配置", "Missing"), badge: `UTC ${data.alert_hour ?? 1}:00`, hint: data.alert_webhook || t("填 Webhook 或跑 cron/tick", "Set a webhook or run cron/tick"), color: data.alert_webhook ? "#16a34a" : "#64748b" },
          { title: t("GEO 节奏", "GEO cadence"), value: data.geo_schedule === "daily" ? t("每天", "Daily") : t("每周", "Weekly"), badge: data.ingest_token ? t("Agent 可用", "Agent ready") : t("登录后可见", "Owner only"), hint: t("15 家问答平台巡检", "15 answer engines"), color: "#ec4899" },
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
              { key: "tracker", label: t("1. 采集脚本", "1. Tracker"), children: <TrackerPane snippetCn={snippetCn} snippetIntl={snippetIntl} identifySample={identifySample} token={token} form={form} isOwner={isOwner} /> },
              { key: "site", label: t("2. 站点档案", "2. Site profile"), children: <ProfilePane /> },
              { key: "orders", label: t("3. 订单接入", "3. Orders"), children: <OrdersPane hooks={hooks} origin={origin} shopifyReady={shopifyReady} wooReady={wooReady} genericReady={genericReady} form={form} isOwner={isOwner} /> },
              { key: "alerts", label: t("4. 告警与 GEO", "4. Alerts & GEO"), children: <AlertsPane data={data} hooks={hooks} origin={origin} /> },
            ]}
          />
        </ProCard>
      </Form>
    </PageContainer>
  );
}

function TrackerPane({ snippetCn, snippetIntl, identifySample, token, form, isOwner }) {
  const t = useT();
  return (
    <Space direction="vertical" size={16} style={{ width: "100%" }}>
      <div className="sl-setup-steps">
        <div className="sl-setup-step">
          <span>01</span>
          <strong>{t("贴脚本", "Paste the tracker")}</strong>
          <p>{t("国内站 / 海外站各贴一段，生产必须带 token。", "One snippet per store; token required in production.")}</p>
        </div>
        <div className="sl-setup-step">
          <span>02</span>
          <strong>{t("认人", "Identify users")}</strong>
          <p>{t("登录后调用 identify，否则「网站用户」是空的。", "Call identify after login or Visitors stays empty.")}</p>
        </div>
        <div className="sl-setup-step">
          <span>03</span>
          <strong>{t("收单", "Take orders")}</strong>
          <p>{t("purchase() 或 Shopify / Woo webhook，只记已支付。", "purchase() or Shopify/Woo webhook; paid only.")}</p>
        </div>
        <div className="sl-setup-step">
          <span>04</span>
          <strong>SEO / GEO</strong>
          <p>{t("爬虫自动记。问答平台按第 4 步的节奏巡检。", "Crawlers are automatic. Answers follow step 4 cadence.")}</p>
        </div>
      </div>
      <Row gutter={[16, 16]}>
        <Col xs={24} xl={14}>
          <CodeBlock title={t("国内站脚本", "China store snippet")} text={snippetCn} hint={t("放在 </body> 前。生产环境不带 data-token 会被拒收。", "Before </body>. Without data-token, production rejects it.")} />
        </Col>
        <Col xs={24} xl={10}>
          <CodeBlock title={t("海外站脚本", "International store snippet")} text={snippetIntl} hint={t("只改 data-region=intl，域名填到 intl_hosts。", "Only data-region=intl changes; list the host in intl_hosts.")} />
        </Col>
      </Row>
      <Row gutter={[16, 16]}>
        <Col xs={24} xl={14}>
          <CodeBlock title={t("认人与下单", "Identify & purchase")} text={identifySample} hint={t("identify / signup 的邮箱会出现在「网站用户」。订单更推荐走 webhook。", "Those emails appear under Visitors. Webhooks are preferred for orders.")} />
        </Col>
        <Col xs={24} xl={10}>
          <div className="sl-setup-note">
            <div className="sl-setup-note-title">
              {token ? <CheckCircleFilled style={{ color: "#16a34a" }} /> : <WarningFilled style={{ color: "#f59e0b" }} />}
              {t("采集密钥", "Collect token")}
            </div>
            <p>{t("tracker 的 data-token。保存后上面的脚本会带上它。", "The tracker data-token. Saved snippets include it.")}</p>
            <Space.Compact style={{ width: "100%" }}>
              <Form.Item name="collect_token" noStyle>
                <Input placeholder="slcol_..." />
              </Form.Item>
              {isOwner && (
                <Button icon={<ReloadOutlined />} onClick={() => form.setFieldValue("collect_token", mint("slcol_"))}>
                  {t("生成", "Generate")}
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
  const t = useT();
  return (
    <Row gutter={[20, 8]}>
      <Col xs={24} lg={12}>
        <Form.Item name="brand" label={t("品牌名", "Brand name")} rules={[{ required: true, message: "GEO 打分要用品牌名" }]}>
          <Input placeholder="流明好物" />
        </Form.Item>
        <Form.Item name="category" label={t("品类", "Category")}>
          <Input placeholder="家居、服饰、保健品" />
        </Form.Item>
        <Form.Item name="brand_aliases" label={t("品牌别名", "Brand aliases")} extra="每行一个。AI 回答里出现这些也算提及。">
          <Input.TextArea rows={3} placeholder={"Lumen Goods\nlumen.shop"} />
        </Form.Item>
        <Form.Item name="keywords" label={t("希望被提到的关键词", "Keywords to be mentioned")} extra="SEO / GEO 打分用，不是广告关键词。">
          <Input.TextArea rows={3} placeholder={"独立站\n亚麻床品"} />
        </Form.Item>
        <Form.Item name="competitors" label={t("竞品名", "Competitors")}>
          <Input.TextArea rows={2} placeholder="每行一个" />
        </Form.Item>
      </Col>
      <Col xs={24} lg={12}>
        <Form.Item name="domains" label={t("官网域名", "Site domains")} extra="用于 GEO 判断「引用了你的官网」。">
          <Input.TextArea rows={2} placeholder={"lumen.shop\nwww.lumen.shop"} />
        </Form.Item>
        <Form.Item
          name="cn_hosts"
          label={t("国内站 host", "China hosts")}
          extra="流量区域看这个，不要只填官网域名。匹配到的记为国内。"
        >
          <Input.TextArea rows={3} placeholder={"lumen.shop\nwww.lumen.shop"} />
        </Form.Item>
        <Form.Item name="intl_hosts" label={t("海外站 host", "International hosts")} extra="没写海外 host 时，国际域名会全部算成国内。">
          <Input.TextArea rows={3} placeholder={"intl.lumen.shop\nwww.lumengoods.com"} />
        </Form.Item>
        <Form.Item name="owned_urls" label={t("自有内容 URL", "Owned content URLs")} extra="GEO 判断「直接引用了你的内容」时用。">
          <Input.TextArea rows={3} placeholder="https://lumen.shop/journal/linen" />
        </Form.Item>
      </Col>
    </Row>
  );
}

function OrdersPane({ hooks, origin, shopifyReady, wooReady, genericReady, form, isOwner }) {
  const t = useT();
  return (
    <Space direction="vertical" size={16} style={{ width: "100%" }}>
      <div className="sl-hook-grid">
        <EndpointCard
          title="Shopify"
          badge={shopifyReady ? t("密钥已填", "Secret set") : ""}
          url={hooks.shopify || `${origin}/api/hooks/shopify`}
          extra="后台 → 通知 → 创建 webhook。事件选 orders/paid。密钥填到下面。"
        />
        <EndpointCard
          title="WooCommerce"
          badge={wooReady ? t("密钥已填", "Secret set") : ""}
          url={hooks.woocommerce || `${origin}/api/hooks/woocommerce`}
          extra="Woo 设置 → 高级 → Webhook。主题选 Order paid / updated。"
        />
        <EndpointCard
          title="通用 JSON"
          badge={genericReady ? t("密钥已填", "Secret set") : ""}
          url={hooks.order || `${origin}/api/hooks/order`}
          extra="请求头 X-Sitelens-Token。同一订单 id 不会重复入账。"
        />
      </div>
      <Row gutter={[20, 8]}>
        <Col xs={24} lg={12}>
          <Form.Item name="shopify_secret" label={t("Shopify webhook secret", "Shopify webhook secret")} extra="校验 X-Shopify-Hmac-Sha256">
            <Input.Password placeholder="从 Shopify 通知页复制" />
          </Form.Item>
          <Form.Item name="woo_secret" label={t("WooCommerce webhook secret", "WooCommerce webhook secret")} extra="校验 X-WC-Webhook-Signature">
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
            title={t("通用订单示例", "Generic order example")}
            text={`curl -X POST ${origin}/api/hooks/order \\\n  -H 'content-type: application/json' \\\n  -H "x-sitelens-token: slhook_..." \\\n  -d '{"id":"A1001","amount":199,"title":"亚麻床品","sku":"linen-1","customer":"ada@shop.test","region":"cn"}'`}
          />
        </Col>
      </Row>
    </Space>
  );
}

function AlertsPane({ data, hooks, origin }) {
  const t = useT();
  return (
    <Row gutter={[20, 16]}>
      <Col xs={24} lg={12}>
        <Form.Item name="geo_schedule" label={t("GEO 巡检节奏", "GEO cadence")} extra="只决定任务是否到期，不会自己去登录问答网站。">
          <Radio.Group optionType="button" options={[{ value: "weekly", label: "每周（推荐）" }, { value: "daily", label: "每天" }]} />
        </Form.Item>
        <Form.Item name="alert_webhook" label={t("日告警 Webhook URL", "Daily alert webhook URL")} extra="每天推近 24 小时 UV、已支付订单、GEO 到期数。">
          <Input placeholder="https://hooks.example/sitelens" />
        </Form.Item>
        <Form.Item name="alert_hour" label={t("日告警小时（UTC）", "Daily alert hour (UTC)")}>
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
          <CodeBlock title={t("日告警 / tick", "Daily alert / tick")} text={`curl -X POST ${hooks.cron || `${origin}/api/cron/tick`} \\\n  -H "x-cron-token: slcron_..."`} />
        </div>
      </Col>
    </Row>
  );
}
