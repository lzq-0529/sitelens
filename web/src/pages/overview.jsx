import { RightOutlined } from "@ant-design/icons";
import { PageContainer, ProCard } from "@ant-design/pro-components";
import { Col, Progress, Radio, Row, Space, Tag } from "antd";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, money, pct, time } from "../api";
import { DailyLines, DaysSwitch, deviceLabel, Kpis, LoadError, RankTable, RegionSwitch, SourceTag, useLoad } from "../components";
import { useLang, useT } from "../i18n";

const FUNNEL_EN = { visit: "Visited site", product: "Viewed product", cart: "Added to cart", checkout: "Began checkout", order: "Ordered" };

export function OverviewPage() {
  const t = useT();
  const { isEn } = useLang();
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
  const SERIES_MAIN = { visitors: t("独立访客 (UV)", "Unique visitors (UV)"), views: t("浏览 (PV)", "Pageviews (PV)"), cart: t("加入购物车", "Add to cart"), order: t("完成下单", "Orders") };
  const SERIES_REGION = { cn_visitors: t("国内站访客", "China visitors"), intl_visitors: t("海外站访客", "International visitors"), cn_views: t("国内站浏览", "China views"), intl_views: t("海外站浏览", "International views") };
  const lineData = useMemo(() => {
    const mapping = chartMode === "region" ? SERIES_REGION : SERIES_MAIN;
    return (s?.site?.series || []).flatMap((row) => Object.entries(mapping).map(([key, label]) => ({ day: row.day, series: label, value: Number(row[key] || 0) })));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [s, chartMode]);
  const top = s?.funnel?.[0]?.count || 0;
  const revenue = extra.data?.revenue;
  const live = extra.data?.live;
  const prev = s?.previous || {};
  const delta = (now_, before) => {
    if (!before) return "";
    const change = Math.round(((now_ - before) / before) * 100);
    return `${change >= 0 ? "▲" : "▼"} ${Math.abs(change)}% ${t("vs 上期", "vs prev")}`;
  };

  return (
    <PageContainer
      subTitle={s?.generated_at ? t(`独立站监控 · 近 ${days} 天（快照 ${time(s.generated_at)}）`, `Store monitoring · last ${days} days (snapshot ${time(s.generated_at)})`) : t("国内外流量、下单漏斗与搜索引擎抓取", "Traffic, order funnel and search crawlers")}
      extra={
        <Space wrap>
          <RegionSwitch value={region} onChange={setRegion} />
          <DaysSwitch value={days} onChange={setDays} />
        </Space>
      }
    >
      <LoadError error={site.error} />
      {live && (
        <div className="sl-live-strip">
          <span className="sl-live-dot" />
          <strong>{t(`实时 · 近 ${live.minutes} 分钟`, `Live · last ${live.minutes} min`)}</strong>
          <span>{live.visitors} {t("访客", "visitors")}</span>
          <span>{live.views} {t("浏览", "views")}</span>
          <span>{live.carts} {t("加购", "carts")}</span>
          <span>{live.orders} {t("下单", "orders")}</span>
          {live.top_pages?.[0] && <span className="sl-live-top">{t("正在看", "Viewing")} {live.top_pages[0].name}</span>}
          {live.top_sources?.[0] && <SourceTag value={live.top_sources[0].name} />}
        </div>
      )}
      <Kpis
        loading={site.loading}
        cols={6}
        items={[
          { title: t("独立访客 (UV)", "Unique visitors (UV)"), value: totalVisitors, badge: t(`浏览 ${s?.site?.views ?? 0} PV`, `${s?.site?.views ?? 0} PV`), hint: `🇨🇳 ${regCn.site_visitors ?? 0} · 🌍 ${regIntl.site_visitors ?? 0}`, sub: delta(totalVisitors, prev.visitors), color: "#16a34a", onClick: () => navigate("/site") },
          { title: t("看商品", "Viewed product"), value: funnelMap.product ?? 0, badge: t(`转化 ${pct(funnelMap.product, totalVisitors)}`, pct(funnelMap.product, totalVisitors)), hint: `🇨🇳 ${regCn.product ?? 0} · 🌍 ${regIntl.product ?? 0}`, sub: delta(funnelMap.product ?? 0, prev.product), color: "#0ea5e9", onClick: () => navigate("/site") },
          { title: t("加入购物车", "Added to cart"), value: funnelMap.cart ?? 0, badge: t(`转化 ${pct(funnelMap.cart, totalVisitors)}`, pct(funnelMap.cart, totalVisitors)), hint: `🇨🇳 ${regCn.cart ?? 0} · 🌍 ${regIntl.cart ?? 0}`, sub: delta(funnelMap.cart ?? 0, prev.cart), color: "#2563eb", onClick: () => navigate("/visitors") },
          { title: t("开始结账", "Began checkout"), value: funnelMap.checkout ?? 0, badge: t(`转化 ${pct(funnelMap.checkout, totalVisitors)}`, pct(funnelMap.checkout, totalVisitors)), hint: t("进入下单页的访客", "Reached checkout"), sub: delta(funnelMap.checkout ?? 0, prev.checkout), color: "#7c3aed", onClick: () => navigate("/orders") },
          { title: t("完成下单", "Orders"), value: funnelMap.order ?? 0, badge: t(`转化 ${pct(funnelMap.order, totalVisitors)}`, pct(funnelMap.order, totalVisitors)), hint: revenue ? t(`近 ${days} 天 ${money(revenue.d30_cents)}`, `${money(revenue.d30_cents)} in ${days}d`) : t("已支付订单", "Paid orders"), sub: delta(funnelMap.order ?? 0, prev.order), color: "#f59e0b", onClick: () => navigate("/orders") },
          { title: t("已识别用户", "Identified users"), value: extra.data?.users?.identified ?? 0, badge: t(`注册 ${extra.data?.users?.signed_up ?? 0}`, `Signups ${extra.data?.users?.signed_up ?? 0}`), hint: t("带邮箱 / 账号的访客", "With email / account"), color: "#ec4899", onClick: () => navigate("/visitors") },
        ]}
      />
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} xl={15}>
          <ProCard
            title={t(`访问量与下单走势（近 ${days} 天）`, `Traffic and orders (last ${days} days)`)}
            bordered
            className="sl-equal-card"
            loading={site.loading}
            extra={
              <Space>
                <Radio.Group size="small" value={chartMode} onChange={(e) => setChartMode(e.target.value)} optionType="button" options={[{ value: "funnel", label: t("访问与下单", "Traffic & orders") }, { value: "region", label: t("国内 vs 海外", "China vs Intl") }]} />
                <a onClick={() => navigate("/site")}>{t("完整站点分析", "Full site analysis")} <RightOutlined /></a>
              </Space>
            }
          >
            <DailyLines data={lineData} height={310} />
          </ProCard>
        </Col>
        <Col xs={24} xl={9}>
          <ProCard title={t("国内外对比 & 下单漏斗", "China vs Intl & funnel")} bordered className="sl-equal-card" loading={site.loading}>
            <div className="sl-region-grid">
              <div className="sl-region-box is-cn">
                <div className="sl-region-box-head"><span>{t("🇨🇳 国内站", "🇨🇳 China store")}</span><Tag color="blue" style={{ margin: 0 }}>CN</Tag></div>
                <div className="sl-region-metrics">
                  <div className="sl-region-metric-item"><span>{t("访客", "Visitors")}</span><strong>{regCn.site_visitors ?? 0}</strong></div>
                  <div className="sl-region-metric-item"><span>{t("加购", "Cart")}</span><strong>{regCn.cart ?? 0}</strong></div>
                  <div className="sl-region-metric-item"><span>{t("下单", "Orders")}</span><strong>{regCn.order ?? 0}</strong></div>
                </div>
              </div>
              <div className="sl-region-box is-global">
                <div className="sl-region-box-head"><span>{t("🌍 海外站", "🌍 International store")}</span><Tag color="purple" style={{ margin: 0 }}>INTL</Tag></div>
                <div className="sl-region-metrics">
                  <div className="sl-region-metric-item"><span>{t("访客", "Visitors")}</span><strong>{regIntl.site_visitors ?? 0}</strong></div>
                  <div className="sl-region-metric-item"><span>{t("加购", "Cart")}</span><strong>{regIntl.cart ?? 0}</strong></div>
                  <div className="sl-region-metric-item"><span>{t("下单", "Orders")}</span><strong>{regIntl.order ?? 0}</strong></div>
                </div>
              </div>
            </div>
            <div className="sl-funnel-list">
              {(s?.funnel || []).map((step) => (
                <div key={step.id} className="sl-funnel-row">
                  <div className="sl-funnel-top">
                    <span>{t(step.label, FUNNEL_EN[step.id] || step.label)}</span>
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
        <Col xs={24} md={8}>
          <RankTable title={t("来源", "Sources")} height={240} rows={s?.site?.referrers} columns={[{ title: t("来源", "Source"), dataIndex: "name", render: (v) => <SourceTag value={v} /> }, { title: t("访客", "Visitors"), dataIndex: "visitors", width: 70, align: "right" }]} />
        </Col>
        <Col xs={24} md={8}>
          <RankTable title={t("热门落地页", "Top landing pages")} height={240} rows={s?.site?.landings} columns={[{ title: t("路径", "Path"), dataIndex: "name", ellipsis: true }, { title: t("访客", "Visitors"), dataIndex: "visitors", width: 70, align: "right" }]} />
        </Col>
        <Col xs={24} md={8}>
          <RankTable title={t("设备 / 浏览器", "Devices")} height={240} rows={s?.site?.devices} columns={[{ title: t("设备", "Device"), dataIndex: "name", render: (v) => deviceLabel(v, isEn) }, { title: t("访客", "Visitors"), dataIndex: "visitors", width: 70, align: "right" }]} />
        </Col>
      </Row>
    </PageContainer>
  );
}
