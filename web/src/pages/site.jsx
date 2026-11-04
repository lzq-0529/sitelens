import { ApiOutlined, EditOutlined } from "@ant-design/icons";
import { PageContainer, ProCard } from "@ant-design/pro-components";
import { App, Button, Col, Form, Input, Modal, Radio, Row, Select, Space, Table, Tabs, Tag, Typography } from "antd";
import { useMemo, useRef, useState } from "react";
import { api, pct, SITE_REGIONS, tableRequest, time } from "../api";
import { useAuth } from "../auth";
import { DailyLines, DataTable, DaysSwitch, engineLabel, Kpis, LoadError, RankTable, RegionSwitch, RegionTag, SourceTag, useLoad } from "../components";
import { useLang, useT } from "../i18n";

const BEHAVIOURS_ZH = { product: "看过商品", cart: "加过购物车", checkout: "开始结账", order: "完成下单", signup: "注册账号" };

export function SitePage() {
  const t = useT();
  const { isOwner } = useAuth();
  const [days, setDays] = useState(28);
  const [region, setRegion] = useState("all");
  const [scope, setScope] = useState("human");
  const visitorsRef = useRef();
  const crawlsRef = useRef();
  const summary = useLoad(() => api(`/api/admin/site/summary?days=${days}&scope=${scope}&region=${region}`), [days, scope, region]);
  const search = useLoad(() => api(`/api/admin/site/search?days=${Math.min(days, 90)}&region=${region}`), [days, region]);
  const geo = useLoad(() => api("/api/admin/site/geo"), []);
  const s = summary.data;
  const SERIES = { visitors: t("独立访客", "Visitors"), views: t("浏览", "Views"), cart: t("加购", "Cart"), order: t("下单", "Orders") };
  const series = useMemo(
    () => (s?.site?.series || []).flatMap((row) => Object.entries(SERIES).map(([key, label]) => ({ day: row.day, series: label, value: row[key] || 0 }))),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [s],
  );

  return (
    <PageContainer
      subTitle={s ? t(`报表 ${time(s.generated_at)} · ${SITE_REGIONS[region]}`, `Report ${time(s.generated_at)} · ${region}`) : t("国内外访问、来源、SEO 抓取、下单漏斗与 GEO", "Visits, sources, SEO crawls, order funnel and GEO")}
      extra={
        <Space wrap>
          <RegionSwitch value={region} onChange={setRegion} />
          <DaysSwitch value={days} onChange={setDays} />
          <Radio.Group value={scope} onChange={(e) => setScope(e.target.value)} optionType="button" options={[{ value: "human", label: t("只看真人", "Humans only") }, { value: "all", label: t("全部访问", "All visits") }]} />
        </Space>
      }
    >
      <LoadError error={summary.error} />
      <Kpis
        loading={summary.loading}
        cols={6}
        items={[
          { title: t("官网访客", "Site visitors"), value: s?.site?.visitors, badge: `${s?.site?.views ?? 0} PV`, hint: t(`国内 ${s?.regions?.cn?.site_visitors ?? 0} · 海外 ${s?.regions?.intl?.site_visitors ?? 0}`, `CN ${s?.regions?.cn?.site_visitors ?? 0} · Intl ${s?.regions?.intl?.site_visitors ?? 0}`), color: "#16a34a" },
          { title: t("看商品", "Viewed product"), value: s?.site?.product, badge: pct(s?.site?.product, s?.site?.visitors), hint: t("浏览商品页", "Product pages"), color: "#0ea5e9" },
          { title: t("加入购物车", "Added to cart"), value: s?.site?.cart, badge: pct(s?.site?.cart, s?.site?.visitors), hint: t("加购人数", "Shoppers"), color: "#2563eb" },
          { title: t("开始结账", "Began checkout"), value: s?.site?.checkout, badge: pct(s?.site?.checkout, s?.site?.visitors), hint: t("进入下单页", "Reached checkout"), color: "#7c3aed" },
          { title: t("完成下单", "Orders"), value: s?.site?.order, badge: pct(s?.site?.order, s?.site?.visitors), hint: t("已支付 / 已下单", "Paid / ordered"), color: "#f59e0b" },
          { title: t("搜索引擎抓取", "Search crawls"), value: search.data?.totals?.hits ?? 0, badge: t(`已验真 ${search.data?.totals?.verified ?? 0}`, `Verified ${search.data?.totals?.verified ?? 0}`), hint: t(`国内 ${search.data?.totals?.cn_hits ?? 0} · 海外 ${search.data?.totals?.intl_hits ?? 0}`, `CN ${search.data?.totals?.cn_hits ?? 0} · Intl ${search.data?.totals?.intl_hits ?? 0}`), color: "#ec4899" },
        ]}
      />
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} xl={16}>
          <ProCard title={t("每日流量与下单趋势", "Daily traffic and orders")} bordered className="sl-equal-card" loading={summary.loading}>
            <DailyLines data={series} height={300} />
          </ProCard>
        </Col>
        <Col xs={24} xl={8}>
          <RankTable title={t("来源", "Sources")} height={300} rows={s?.site?.referrers} columns={[{ title: t("来源", "Source"), dataIndex: "name", render: (v) => <SourceTag value={v} /> }, { title: t("访客", "Visitors"), dataIndex: "visitors", width: 64, align: "right" }]} />
        </Col>
      </Row>
      <ProCard bordered bodyStyle={{ paddingTop: 4 }}>
        <Tabs
          items={[
            { key: "visitors", label: t("访客明细", "Visitors"), children: <VisitorTable actionRef={visitorsRef} days={days} scope={scope} region={region} /> },
            { key: "engines", label: t("搜索引擎与 AI 抓取", "Search & AI crawlers"), children: <EngineTable search={search} /> },
            { key: "geo", label: t("AI 回答引用监测 (GEO)", "AI citation watch (GEO)"), children: <GeoPanel geo={geo} isOwner={isOwner} /> },
            { key: "crawls", label: t("爬虫日志", "Crawl log"), children: <CrawlTable actionRef={crawlsRef} days={days} region={region} /> },
          ]}
        />
      </ProCard>
    </PageContainer>
  );
}

function VisitorTable({ actionRef, days, scope, region }) {
  const t = useT();
  const { isEn } = useLang();
  const BEHAVIOURS = isEn ? { product: "Viewed product", cart: "Added to cart", checkout: "Began checkout", order: "Ordered", signup: "Signed up" } : BEHAVIOURS_ZH;
  return (
    <DataTable
      headerTitle={t("访客明细", "Visitor details")}
      actionRef={actionRef}
      params={{ days, scope, region }}
      request={tableRequest("/api/admin/site/visitors")}
      cardBordered={false}
      columns={[
        { title: t("关键词", "Keyword"), dataIndex: "q", hideInTable: true, filter: true, fieldProps: { placeholder: t("搜索来源（如知乎/小红书/Google/Reddit）、账号、设备、IP 或路径", "Source (Zhihu/Google/Reddit…), account, device, IP") } },
        { title: t("站点", "Site"), dataIndex: "region", width: 90, render: (_, row) => <RegionTag region={row.region} /> },
        { title: t("类型", "Type"), dataIndex: "kind_label", width: 90, render: (v) => (isEn ? { "真人": "Human", "爬虫/机器人": "Bot", "未知": "Unknown" }[v] || v : v) },
        {
          title: t("转化行为", "Behaviour"),
          dataIndex: "behaviour",
          valueType: "select",
          valueEnum: BEHAVIOURS,
          filter: true,
          render: (_, row) => (
            <Space size={4} wrap>
              {row.viewed_item && <Tag color="blue">{t("看商品", "Viewed")}</Tag>}
              {row.added_cart && <Tag color="cyan">{t("加购", "Cart")}</Tag>}
              {row.began_checkout && <Tag color="purple">{t("结账", "Checkout")}</Tag>}
              {row.ordered && <Tag color="green">{t("下单", "Ordered")}</Tag>}
              {row.signed_up && <Tag>{t("注册", "Signup")}</Tag>}
              {!row.viewed_item && !row.added_cart && !row.ordered && t("浏览", "Browsed")}
            </Space>
          ),
        },
        { title: t("首次", "First"), dataIndex: "first", width: 110 },
        { title: t("最近", "Last"), dataIndex: "last", width: 110 },
        { title: t("来源", "Source"), dataIndex: "source", render: (v) => <SourceTag value={v} /> },
        { title: t("设备", "Device"), dataIndex: "device", ellipsis: true },
        { title: t("账号", "Account"), dataIndex: "account", width: 160, ellipsis: true, renderText: (v) => v || "—" },
        { title: t("浏览", "Views"), dataIndex: "site_views", width: 70, align: "right" },
        { title: t("IP（已打码）", "IP (masked)"), dataIndex: "ip", width: 130 },
      ]}
    />
  );
}

function EngineTable({ search }) {
  const t = useT();
  const { isEn } = useLang();
  return (
    <>
      <LoadError error={search.error} />
      <Table
        rowKey="id"
        size="middle"
        loading={search.loading}
        dataSource={search.data?.engines || []}
        pagination={{ pageSize: 20 }}
        columns={[
          { title: t("引擎 / 模型", "Engine / model"), dataIndex: "label", render: (v) => engineLabel(v, isEn) },
          { title: t("抓取次数", "Crawls"), dataIndex: "hits", width: 100, align: "right" },
          { title: t("国内", "CN"), dataIndex: "cn_hits", width: 80, align: "right" },
          { title: t("海外", "Intl"), dataIndex: "intl_hits", width: 80, align: "right" },
          { title: t("页面数", "Pages"), dataIndex: "page_count", width: 80, align: "right" },
          { title: t("最近到访", "Last visit"), dataIndex: "last", width: 160 },
        ]}
      />
    </>
  );
}

function CrawlTable({ actionRef, days, region }) {
  const t = useT();
  const { isEn } = useLang();
  return (
    <DataTable
      headerTitle={t("爬虫抓取", "Crawler hits")}
      actionRef={actionRef}
      params={{ days, region }}
      request={tableRequest("/api/admin/site/crawls")}
      cardBordered={false}
      columns={[
        { title: t("关键词", "Keyword"), dataIndex: "q", hideInTable: true, filter: true, fieldProps: { placeholder: t("搜索引擎、路径或 IP", "Engine, path or IP") } },
        { title: t("时间", "Time"), dataIndex: "time", width: 110 },
        { title: t("站点", "Site"), dataIndex: "region", width: 90, render: (_, row) => <RegionTag region={row.region} /> },
        { title: t("引擎", "Engine"), dataIndex: "label", width: 150, render: (v) => engineLabel(v, isEn) },
        { title: t("路径", "Path"), dataIndex: "path", ellipsis: true },
        { title: t("状态", "Status"), dataIndex: "status", width: 80 },
        { title: t("IP（已打码）", "IP (masked)"), dataIndex: "ip", width: 130 },
      ]}
    />
  );
}

function GeoPanel({ geo, isOwner }) {
  const t = useT();
  const { isEn } = useLang();
  const { message } = App.useApp();
  const [open, setOpen] = useState(false);
  const [tab, setTab] = useState("prompts");
  const [form] = Form.useForm();
  const data = geo.data || {};
  const summary = data.summary || {};
  const prompts = data.prompts || { cn: [], intl: [] };
  const token = data.ingest_token || "slgeo_***";

  async function mutate(body, ok = "已更新") {
    try {
      await api("/api/admin/site/geo/prompts", { method: "POST", body });
      message.success(ok);
      geo.reload();
    } catch (exc) {
      message.error(exc.message);
    }
  }

  return (
    <Space direction="vertical" size={16} style={{ width: "100%" }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, background: "#f8fafc", padding: 12, borderRadius: 10, border: "1px solid #e2e8f0" }}>
        <Space wrap>
          <Typography.Text strong>{t("15 家问答平台 · 默认可按周交给 Grok / Muse 巡检", "15 answer engines · weekly Grok / Muse checks by default")}</Typography.Text>
          <Tag color="blue">{t("已覆盖", "Covered")} {summary.tested_platforms ?? 0} / {summary.total_platforms ?? 15}</Tag>
          <Tag color="orange">{t("待巡检", "Due")} {summary.due_platforms ?? 0}</Tag>
          <Tag color="green">{t("官网被引用", "Site cited")} {summary.owned_cited_count ?? 0}</Tag>
          <Tag color="purple">{t("品牌提及", "Brand mentions")} {summary.brand_mention_count ?? 0}</Tag>
        </Space>
        {isOwner && (
          <Space>
            <Button icon={<EditOutlined />} onClick={() => { setTab("prompts"); setOpen(true); }}>{t("提问词", "Prompts")}</Button>
            <Button icon={<ApiOutlined />} onClick={() => { setTab("api"); setOpen(true); }}>{t("Grok / Muse 接口", "Grok / Muse API")}</Button>
          </Space>
        )}
      </div>
      <Table
        rowKey="id"
        size="small"
        loading={geo.loading}
        dataSource={data.platforms || []}
        pagination={false}
        columns={[
          { title: t("平台", "Platform"), dataIndex: "label", render: (val, row) => <a href={row.url} target="_blank" rel="noreferrer">{engineLabel(val, isEn)}</a> },
          { title: t("区域", "Region"), dataIndex: "region_label", width: 100, render: (val) => <Tag color={val === "海外" ? "purple" : "blue"}>{engineLabel(val, isEn)}</Tag> },
          { title: t("节奏", "Cadence"), dataIndex: "schedule", width: 90, render: (v) => engineLabel(v === "daily" ? "每天" : "每周", isEn) },
          { title: t("已测", "Tested"), dataIndex: "tested", width: 80, render: (v) => (v ? t("是", "Yes") : t("待测", "Pending")) },
          { title: t("引用", "Citations"), dataIndex: "direct_cited", width: 90 },
          { title: t("最佳排名", "Best rank"), dataIndex: "best_rank", width: 100, render: (v) => v || "—" },
          { title: t("最近回传", "Last report"), dataIndex: "updated_at", width: 180, render: (v) => time(v) },
        ]}
      />
      <Table
        rowKey="id"
        size="small"
        dataSource={[...(data.rows || [])].sort((a, b) => {
          const ascii = (x) => (/[\u4e00-\u9fff]/.test(x?.query || "") ? 0 : 1);
          return isEn ? ascii(b) - ascii(a) : ascii(a) - ascii(b);
        })}
        pagination={{ pageSize: 8 }}
        columns={[
          { title: t("平台", "Platform"), dataIndex: "engine_label", width: 140, render: (v) => engineLabel(v, isEn) },
          { title: t("提问", "Prompt"), dataIndex: "query", ellipsis: true },
          { title: t("摘要", "Answer excerpt"), dataIndex: "answer_excerpt", ellipsis: true },
          { title: t("引用", "Cited"), dataIndex: "cited", width: 80, render: (v) => (v ? <Tag color="green">{t("是", "Yes")}</Tag> : t("否", "No")) },
          { title: t("品牌", "Brand"), dataIndex: "brand_mentioned", width: 80, render: (v) => (v ? t("是", "Yes") : t("否", "No")) },
        ]}
      />
      <Modal title={t("GEO 提问词与 Agent 接口", "GEO prompts & agent API")} open={open} onCancel={() => setOpen(false)} footer={null} width={760}>
        <Tabs
          activeKey={tab}
          onChange={setTab}
          items={[
            {
              key: "prompts",
              label: t("提问词", "Prompts"),
              children: (
                <Space direction="vertical" style={{ width: "100%" }}>
                  <Typography.Text type="secondary">国内 {(prompts.cn || []).length} 条 · 海外 {(prompts.intl || []).length} 条。Agent 每周拉取后按这些词去问。</Typography.Text>
                  {(prompts.cn || []).map((item) => (
                    <Space key={item} style={{ width: "100%", justifyContent: "space-between" }}>
                      <span>{item}</span>
                      {isOwner && <a onClick={() => mutate({ action: "delete", region: "cn", query: item }, "已删除")}>删除</a>}
                    </Space>
                  ))}
                  <Input.Search
                    enterButton="添加国内提问"
                    onSearch={(value) => value && mutate({ action: "add", region: "cn", query: value }, "已添加")}
                  />
                  {(prompts.intl || []).map((item) => (
                    <Space key={item} style={{ width: "100%", justifyContent: "space-between" }}>
                      <span>{item}</span>
                      {isOwner && <a onClick={() => mutate({ action: "delete", region: "intl", query: item }, "已删除")}>删除</a>}
                    </Space>
                  ))}
                  <Input.Search enterButton="Add English prompt" onSearch={(value) => value && mutate({ action: "add", region: "intl", query: value }, "已添加")} />
                </Space>
              ),
            },
            {
              key: "api",
              label: t("Grok / Muse", "Grok / Muse"),
              children: (
                <Space direction="vertical" style={{ width: "100%" }}>
                  <Typography.Paragraph copyable={{ text: token }}>Token：{token}</Typography.Paragraph>
                  <Typography.Paragraph>
                    <pre style={{ whiteSpace: "pre-wrap", background: "#f8fafc", padding: 12, borderRadius: 8 }}>
{`curl -sS "$HOST/api/geo/tasks" -H "X-Geo-Token: ${token}"
curl -sS -X POST "$HOST/api/geo/ingest" \\
  -H "Content-Type: application/json" -H "X-Geo-Token: ${token}" \\
  -d '{"agent":"grok","items":[{"platform":"deepseek","query":"...","answer":"...","sources":["https://your.site"]}]}'`}
                    </pre>
                  </Typography.Paragraph>
                  <Form form={form} layout="vertical" onFinish={async (values) => {
                    await api("/api/admin/site/geo/ingest", { method: "POST", body: { platform: values.platform, source_mode: "manual", results: [{ query: values.query, answer: values.answer, sources: String(values.sources || "").split(/\n/).filter(Boolean) }] } });
                    message.success("已录入");
                    geo.reload();
                  }}>
                    <Form.Item name="platform" label="平台" initialValue="deepseek"><Select options={(data.platforms || []).map((p) => ({ value: p.id, label: p.label }))} /></Form.Item>
                    <Form.Item name="query" label="提问" rules={[{ required: true }]}><Input /></Form.Item>
                    <Form.Item name="answer" label="回答" rules={[{ required: true }]}><Input.TextArea rows={4} /></Form.Item>
                    <Form.Item name="sources" label="引用来源（每行一个 URL）"><Input.TextArea rows={3} /></Form.Item>
                    <Button type="primary" htmlType="submit">手工录入</Button>
                  </Form>
                </Space>
              ),
            },
          ]}
        />
      </Modal>
    </Space>
  );
}
