import { RightOutlined } from "@ant-design/icons";
import { PageContainer, ProCard } from "@ant-design/pro-components";
import { Col, Progress, Radio, Row, Space, Tag } from "antd";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, money, pct, time } from "../api";
import { DailyLines, DaysSwitch, Kpis, LoadError, RankTable, RegionSwitch, SourceTag, useLoad } from "../components";

const SERIES_MAIN = { visitors: "独立访客 (UV)", views: "浏览 (PV)", cart: "加入购物车", order: "完成下单" };
const SERIES_REGION = { cn_visitors: "国内站访客", intl_visitors: "海外站访客", cn_views: "国内站浏览", intl_views: "海外站浏览" };

export function OverviewPage() {
  const navigate = useNavigate();
  const [days, setDays] = useState(28);
  const [region, setRegion] = useState("all");
  const [chartMode, setChartMode] = useState("funnel");
  const site = useLoad(() => api(`/api/admin/site/summary?days=${days}&scope=human&region=${region}`), [days, region]);
  const extra = useLoad(() => api(`/api/admin/overview?days=${days}&region=${region}`), [days, region]);
  const s = site.data;
  const funnelMap = Object.fromEntries((s?.funnel || []).map((step) => [step.id, step.count]));
  const regCn = s?.regions?.cn || {};
  const regIntl = s?.regions?.intl || {};
  const totalVisitors = s?.site?.visitors ?? 0;
  const lineData = useMemo(() => {
    const mapping = chartMode === "region" ? SERIES_REGION : SERIES_MAIN;
    return (s?.site?.series || []).flatMap((row) => Object.entries(mapping).map(([key, label]) => ({ day: row.day, series: label, value: Number(row[key] || 0) })));
  }, [s, chartMode]);
  const top = s?.funnel?.[0]?.count || 0;
  const revenue = extra.data?.revenue;

  return (
    <PageContainer
      subTitle={s?.generated_at ? `独立站监控 · 近 ${days} 天（快照 ${time(s.generated_at)}）` : "国内外流量、下单漏斗与搜索引擎抓取"}
      extra={
        <Space wrap>
          <RegionSwitch value={region} onChange={setRegion} />
          <DaysSwitch value={days} onChange={setDays} />
        </Space>
      }
    >
      <LoadError error={site.error} />
      <Kpis
        loading={site.loading}
        cols={6}
        items={[
          { title: "独立访客 (UV)", value: totalVisitors, badge: `浏览 ${s?.site?.views ?? 0} PV`, hint: `🇨🇳 ${regCn.site_visitors ?? 0} · 🌍 ${regIntl.site_visitors ?? 0}`, color: "#16a34a", onClick: () => navigate("/site") },
          { title: "看商品", value: funnelMap.product ?? 0, badge: `转化 ${pct(funnelMap.product, totalVisitors)}`, hint: `🇨🇳 ${regCn.product ?? 0} · 🌍 ${regIntl.product ?? 0}`, color: "#0ea5e9", onClick: () => navigate("/site") },
          { title: "加入购物车", value: funnelMap.cart ?? 0, badge: `转化 ${pct(funnelMap.cart, totalVisitors)}`, hint: `🇨🇳 ${regCn.cart ?? 0} · 🌍 ${regIntl.cart ?? 0}`, color: "#2563eb", onClick: () => navigate("/visitors") },
          { title: "开始结账", value: funnelMap.checkout ?? 0, badge: `转化 ${pct(funnelMap.checkout, totalVisitors)}`, hint: "进入下单页的访客", color: "#7c3aed", onClick: () => navigate("/orders") },
          { title: "完成下单", value: funnelMap.order ?? 0, badge: `转化 ${pct(funnelMap.order, totalVisitors)}`, hint: revenue ? `近 ${days} 天 ${money(revenue.d30_cents)}` : "已支付订单", color: "#f59e0b", onClick: () => navigate("/orders") },
          { title: "已识别用户", value: extra.data?.users?.identified ?? 0, badge: `注册 ${extra.data?.users?.signed_up ?? 0}`, hint: "带邮箱 / 账号的访客", color: "#ec4899", onClick: () => navigate("/visitors") },
        ]}
      />
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} xl={15}>
          <ProCard
            title={`访问量与下单走势（近 ${days} 天）`}
            bordered
            className="sl-equal-card"
            loading={site.loading}
            extra={
              <Space>
                <Radio.Group size="small" value={chartMode} onChange={(e) => setChartMode(e.target.value)} optionType="button" options={[{ value: "funnel", label: "访问与下单" }, { value: "region", label: "国内 vs 海外" }]} />
                <a onClick={() => navigate("/site")}>完整站点分析 <RightOutlined /></a>
              </Space>
            }
          >
            <DailyLines data={lineData} height={310} />
          </ProCard>
        </Col>
        <Col xs={24} xl={9}>
          <ProCard title="国内外对比 & 下单漏斗" bordered className="sl-equal-card" loading={site.loading}>
            <div className="sl-region-grid">
              <div className="sl-region-box is-cn">
                <div className="sl-region-box-head"><span>🇨🇳 国内站</span><Tag color="blue" style={{ margin: 0 }}>CN</Tag></div>
                <div className="sl-region-metrics">
                  <div className="sl-region-metric-item"><span>访客</span><strong>{regCn.site_visitors ?? 0}</strong></div>
                  <div className="sl-region-metric-item"><span>加购</span><strong>{regCn.cart ?? 0}</strong></div>
                  <div className="sl-region-metric-item"><span>下单</span><strong>{regCn.order ?? 0}</strong></div>
                </div>
              </div>
              <div className="sl-region-box is-global">
                <div className="sl-region-box-head"><span>🌍 海外站</span><Tag color="purple" style={{ margin: 0 }}>INTL</Tag></div>
                <div className="sl-region-metrics">
                  <div className="sl-region-metric-item"><span>访客</span><strong>{regIntl.site_visitors ?? 0}</strong></div>
                  <div className="sl-region-metric-item"><span>加购</span><strong>{regIntl.cart ?? 0}</strong></div>
                  <div className="sl-region-metric-item"><span>下单</span><strong>{regIntl.order ?? 0}</strong></div>
                </div>
              </div>
            </div>
            <div className="sl-funnel-list">
              {(s?.funnel || []).map((step) => (
                <div key={step.id} className="sl-funnel-row">
                  <div className="sl-funnel-top">
                    <span>{step.label}</span>
                    <b>{step.count}</b>
                  </div>
                  <Progress percent={top ? Math.round((step.count / top) * 100) : 0} showInfo={false} size="small" strokeColor="#16a34a" />
                </div>
              ))}
            </div>
          </ProCard>
        </Col>
      </Row>
      <Row gutter={[16, 16]}>
        <Col xs={24} md={12}>
          <RankTable title="来源" height={240} rows={s?.site?.referrers} columns={[{ title: "来源", dataIndex: "name", render: (v) => <SourceTag value={v} /> }, { title: "访客", dataIndex: "visitors", width: 70, align: "right" }]} />
        </Col>
        <Col xs={24} md={12}>
          <RankTable title="热门落地页" height={240} rows={s?.site?.landings} columns={[{ title: "路径", dataIndex: "name", ellipsis: true }, { title: "访客", dataIndex: "visitors", width: 70, align: "right" }]} />
        </Col>
      </Row>
    </PageContainer>
  );
}
