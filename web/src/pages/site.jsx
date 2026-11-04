import { ApiOutlined, EditOutlined } from "@ant-design/icons";
import { PageContainer, ProCard } from "@ant-design/pro-components";
import { App, Button, Col, Form, Input, Modal, Radio, Row, Select, Space, Table, Tabs, Tag, Typography } from "antd";
import { useMemo, useRef, useState } from "react";
import { api, pct, SITE_REGIONS, tableRequest, time } from "../api";
import { useAuth } from "../auth";
import { DailyLines, DataTable, DaysSwitch, Kpis, LoadError, RankTable, RegionSwitch, RegionTag, SourceTag, useLoad } from "../components";

const SERIES = { visitors: "独立访客", views: "浏览", cart: "加购", order: "下单" };
const BEHAVIOURS = { product: "看过商品", cart: "加过购物车", checkout: "开始结账", order: "完成下单", signup: "注册账号" };

export function SitePage() {
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
  const series = useMemo(
    () => (s?.site?.series || []).flatMap((row) => Object.entries(SERIES).map(([key, label]) => ({ day: row.day, series: label, value: row[key] || 0 }))),
    [s],
  );

  return (
    <PageContainer
      subTitle={s ? `报表 ${time(s.generated_at)} · ${SITE_REGIONS[region]}` : "国内外访问、来源、SEO 抓取、下单漏斗与 GEO"}
      extra={
        <Space wrap>
          <RegionSwitch value={region} onChange={setRegion} />
          <DaysSwitch value={days} onChange={setDays} />
          <Radio.Group value={scope} onChange={(e) => setScope(e.target.value)} optionType="button" options={[{ value: "human", label: "只看真人" }, { value: "all", label: "全部访问" }]} />
        </Space>
      }
    >
      <LoadError error={summary.error} />
      <Kpis
        loading={summary.loading}
        cols={6}
        items={[
          { title: "官网访客", value: s?.site?.visitors, badge: `${s?.site?.views ?? 0} PV`, hint: `国内 ${s?.regions?.cn?.site_visitors ?? 0} · 海外 ${s?.regions?.intl?.site_visitors ?? 0}`, color: "#16a34a" },
          { title: "看商品", value: s?.site?.product, badge: `转化 ${pct(s?.site?.product, s?.site?.visitors)}`, hint: "浏览商品页", color: "#0ea5e9" },
          { title: "加入购物车", value: s?.site?.cart, badge: `转化 ${pct(s?.site?.cart, s?.site?.visitors)}`, hint: "加购人数", color: "#2563eb" },
          { title: "开始结账", value: s?.site?.checkout, badge: `转化 ${pct(s?.site?.checkout, s?.site?.visitors)}`, hint: "进入下单页", color: "#7c3aed" },
          { title: "完成下单", value: s?.site?.order, badge: `转化 ${pct(s?.site?.order, s?.site?.visitors)}`, hint: "已支付 / 已下单", color: "#f59e0b" },
          { title: "搜索引擎抓取", value: search.data?.totals?.hits ?? 0, badge: `已验真 ${search.data?.totals?.verified ?? 0}`, hint: `国内 ${search.data?.totals?.cn_hits ?? 0} · 海外 ${search.data?.totals?.intl_hits ?? 0}`, color: "#ec4899" },
        ]}
      />
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} xl={16}>
          <ProCard title="每日流量与下单趋势" bordered className="sl-equal-card" loading={summary.loading}>
            <DailyLines data={series} height={300} />
          </ProCard>
        </Col>
        <Col xs={24} xl={8}>
          <RankTable title="来源" height={300} rows={s?.site?.referrers} columns={[{ title: "来源", dataIndex: "name", render: (v) => <SourceTag value={v} /> }, { title: "访客", dataIndex: "visitors", width: 64, align: "right" }]} />
        </Col>
      </Row>
      <ProCard bordered bodyStyle={{ paddingTop: 4 }}>
        <Tabs
          items={[
            { key: "visitors", label: "访客明细", children: <VisitorTable actionRef={visitorsRef} days={days} scope={scope} region={region} /> },
            { key: "engines", label: "搜索引擎与 AI 抓取", children: <EngineTable search={search} /> },
            { key: "geo", label: "AI 回答引用监测 (GEO)", children: <GeoPanel geo={geo} isOwner={isOwner} /> },
            { key: "crawls", label: "爬虫日志", children: <CrawlTable actionRef={crawlsRef} days={days} region={region} /> },
          ]}
        />
      </ProCard>
    </PageContainer>
  );
}

function VisitorTable({ actionRef, days, scope, region }) {
  return (
    <DataTable
      headerTitle="访客明细"
      actionRef={actionRef}
      params={{ days, scope, region }}
      request={tableRequest("/api/admin/site/visitors")}
      cardBordered={false}
      columns={[
        { title: "关键词", dataIndex: "q", hideInTable: true, filter: true },
        { title: "站点", dataIndex: "region", width: 90, render: (_, row) => <RegionTag region={row.region} /> },
        { title: "类型", dataIndex: "kind_label", width: 80 },
        {
          title: "转化行为",
          dataIndex: "behaviour",
          valueType: "select",
          valueEnum: BEHAVIOURS,
          filter: true,
          render: (_, row) => (
            <Space size={4} wrap>
              {row.viewed_item && <Tag color="blue">看商品</Tag>}
              {row.added_cart && <Tag color="cyan">加购</Tag>}
              {row.began_checkout && <Tag color="purple">结账</Tag>}
              {row.ordered && <Tag color="green">下单</Tag>}
              {row.signed_up && <Tag>注册</Tag>}
              {!row.viewed_item && !row.added_cart && !row.ordered && "浏览"}
            </Space>
          ),
        },
        { title: "首次", dataIndex: "first", width: 110 },
        { title: "最近", dataIndex: "last", width: 110 },
        { title: "来源", dataIndex: "source", render: (v) => <SourceTag value={v} /> },
        { title: "设备", dataIndex: "device", ellipsis: true },
        { title: "账号", dataIndex: "account", width: 160, renderText: (v) => v || "—" },
        { title: "浏览", dataIndex: "site_views", width: 70, align: "right" },
        { title: "IP", dataIndex: "ip", width: 140 },
      ]}
    />
  );
}

function EngineTable({ search }) {
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
          { title: "引擎 / 模型", dataIndex: "label" },
          { title: "抓取次数", dataIndex: "hits", width: 100, align: "right" },
          { title: "国内", dataIndex: "cn_hits", width: 80, align: "right" },
          { title: "海外", dataIndex: "intl_hits", width: 80, align: "right" },
          { title: "页面数", dataIndex: "page_count", width: 80, align: "right" },
          { title: "最近到访", dataIndex: "last", width: 160 },
        ]}
      />
    </>
  );
}

function CrawlTable({ actionRef, days, region }) {
  return (
    <DataTable
      headerTitle="爬虫抓取"
      actionRef={actionRef}
      params={{ days, region }}
      request={tableRequest("/api/admin/site/crawls")}
      cardBordered={false}
      columns={[
        { title: "关键词", dataIndex: "q", hideInTable: true, filter: true },
        { title: "时间", dataIndex: "time", width: 110 },
        { title: "站点", dataIndex: "region", width: 90, render: (_, row) => <RegionTag region={row.region} /> },
        { title: "引擎", dataIndex: "label", width: 140 },
        { title: "路径", dataIndex: "path", ellipsis: true },
        { title: "状态", dataIndex: "status", width: 80 },
        { title: "IP", dataIndex: "ip", width: 140 },
      ]}
    />
  );
}

function GeoPanel({ geo, isOwner }) {
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
          <Typography.Text strong>15 家问答平台 · 默认可按周交给 Grok / Muse 巡检</Typography.Text>
          <Tag color="blue">已覆盖 {summary.tested_platforms ?? 0} / {summary.total_platforms ?? 15}</Tag>
          <Tag color="orange">待巡检 {summary.due_platforms ?? 0}</Tag>
          <Tag color="green">官网被引用 {summary.owned_cited_count ?? 0}</Tag>
          <Tag color="purple">品牌提及 {summary.brand_mention_count ?? 0}</Tag>
        </Space>
        {isOwner && (
          <Space>
            <Button icon={<EditOutlined />} onClick={() => { setTab("prompts"); setOpen(true); }}>提问词</Button>
            <Button icon={<ApiOutlined />} onClick={() => { setTab("api"); setOpen(true); }}>Grok / Muse 接口</Button>
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
          { title: "平台", dataIndex: "label", render: (val, row) => <a href={row.url} target="_blank" rel="noreferrer">{val}</a> },
          { title: "区域", dataIndex: "region_label", width: 90, render: (val) => <Tag color={val === "海外" ? "purple" : "blue"}>{val}</Tag> },
          { title: "节奏", dataIndex: "schedule", width: 80 },
          { title: "已测", dataIndex: "tested", width: 70, render: (v) => (v ? "是" : "待测") },
          { title: "引用", dataIndex: "direct_cited", width: 70 },
          { title: "最佳排名", dataIndex: "best_rank", width: 90, render: (v) => v || "—" },
          { title: "最近回传", dataIndex: "updated_at", width: 180, render: (v) => time(v) },
        ]}
      />
      <Table
        rowKey="id"
        size="small"
        dataSource={data.rows || []}
        pagination={{ pageSize: 8 }}
        columns={[
          { title: "平台", dataIndex: "engine_label", width: 140 },
          { title: "提问", dataIndex: "query", ellipsis: true },
          { title: "摘要", dataIndex: "answer_excerpt", ellipsis: true },
          { title: "引用", dataIndex: "cited", width: 70, render: (v) => (v ? <Tag color="green">是</Tag> : "否") },
          { title: "品牌", dataIndex: "brand_mentioned", width: 70, render: (v) => (v ? "是" : "否") },
        ]}
      />
      <Modal title="GEO 提问词与 Agent 接口" open={open} onCancel={() => setOpen(false)} footer={null} width={760}>
        <Tabs
          activeKey={tab}
          onChange={setTab}
          items={[
            {
              key: "prompts",
              label: "提问词",
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
              label: "Grok / Muse",
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
