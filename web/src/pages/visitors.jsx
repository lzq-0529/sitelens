import { PageContainer, ProCard } from "@ant-design/pro-components";
import { Space, Tabs, Tag } from "antd";
import { useRef, useState } from "react";
import { api, SITE_REGIONS, tableRequest, time } from "../api";
import { DataTable, deviceLabel, Kpis, LoadError, RegionSwitch, RegionTag, SourceTag, useLoad } from "../components";
import { useLang, useT } from "../i18n";

export function VisitorsPage() {
  const t = useT();
  const { isEn } = useLang();
  const [region, setRegion] = useState("all");
  const usersRef = useRef();
  const eventsRef = useRef();
  const summary = useLoad(() => api(`/api/admin/visitors/summary?region=${region}`), [region]);
  const s = summary.data || {};

  const EVENTS = {
    pageview: t("浏览", "Pageview"),
    view_item: t("看商品", "View item"),
    add_to_cart: t("加购", "Add to cart"),
    begin_checkout: t("结账", "Checkout"),
    purchase: t("下单", "Purchase"),
    signup: t("注册", "Signup"),
    identify: t("识别", "Identify"),
  };
  const BEHAVIOURS = {
    product: t("看过商品", "Viewed product"),
    cart: t("加过购物车", "Added to cart"),
    checkout: t("开始结账", "Began checkout"),
    order: t("完成下单", "Ordered"),
    signup: t("注册账号", "Signed up"),
  };

  return (
    <PageContainer
      subTitle={t(`独立站访客、已识别账号与点击/下单行为（${SITE_REGIONS[region]}）`, `Store visitors, identified accounts and click/order behaviour (${isEn ? { all: "All regions", cn: "China", intl: "International" }[region] : SITE_REGIONS[region]})`)}
      extra={<RegionSwitch value={region} onChange={setRegion} />}
    >
      <LoadError error={summary.error} />
      <Kpis
        loading={summary.loading}
        cols={5}
        items={[
          { title: t("访客", "Visitors"), value: s.visitors, hint: t(`国内 ${s.cn ?? 0} · 海外 ${s.intl ?? 0}`, `CN ${s.cn ?? 0} · Intl ${s.intl ?? 0}`), color: "#16a34a" },
          { title: t("已识别账号", "Identified"), value: s.identified, hint: t("带邮箱或用户 ID", "With email or user ID"), color: "#0ea5e9" },
          { title: t("新注册", "Signups"), value: s.signed_up, hint: t("signup 事件", "signup events"), color: "#2563eb" },
          { title: t("加过购物车", "Added to cart"), value: s.cart, hint: t("至少一次加购", "At least one add-to-cart"), color: "#7c3aed" },
          { title: t("完成下单", "Ordered"), value: s.ordered, hint: t("至少一笔订单", "At least one order"), color: "#f59e0b" },
        ]}
      />
      <ProCard bordered bodyStyle={{ paddingTop: 4 }}>
        <Tabs
          items={[
            {
              key: "users",
              label: t("已识别用户", "Identified users"),
              children: (
                <DataTable
                  headerTitle={t("带账号的访客", "Visitors with accounts")}
                  actionRef={usersRef}
                  params={{ region, identified: true, days: 90 }}
                  request={tableRequest("/api/admin/site/visitors", { identified: true, days: 90 })}
                  cardBordered={false}
                  columns={[
                    { title: t("关键词", "Keyword"), dataIndex: "q", hideInTable: true, filter: true, fieldProps: { placeholder: t("搜索账号、来源（如知乎/小红书/Google/Reddit）、设备或 IP", "Account, source (Zhihu/Reddit/Google…), device or IP") } },
                    {
                      title: t("转化行为", "Behaviour"),
                      dataIndex: "behaviour",
                      hideInTable: true,
                      valueType: "select",
                      valueEnum: BEHAVIOURS,
                      filter: true,
                    },
                    { title: t("账号", "Account"), dataIndex: "account", ellipsis: true },
                    { title: t("站点", "Site"), dataIndex: "region", width: 90, render: (_, row) => <RegionTag region={row.region} /> },
                    { title: t("来源", "Source"), dataIndex: "source", width: 130, render: (v) => <SourceTag value={v} /> },
                    { title: t("设备", "Device"), dataIndex: "device", width: 140, ellipsis: true, render: (_, row) => deviceLabel(row.device, isEn) },
                    { title: t("IP（已打码）", "IP (masked)"), dataIndex: "ip", width: 130 },
                    { title: t("浏览", "Views"), dataIndex: "site_views", width: 70, align: "right" },
                    {
                      title: t("行为", "Actions"),
                      render: (_, row) => (
                        <Space size={4} wrap>
                          {row.viewed_item && <Tag color="blue">{t("看商品", "Viewed")}</Tag>}
                          {row.added_cart && <Tag color="cyan">{t("加购", "Cart")}</Tag>}
                          {row.began_checkout && <Tag color="purple">{t("结账", "Checkout")}</Tag>}
                          {row.ordered && <Tag color="green">{t("下单", "Ordered")}</Tag>}
                          {row.signed_up && <Tag>{t("注册", "Signup")}</Tag>}
                        </Space>
                      ),
                    },
                    { title: t("最近", "Last seen"), dataIndex: "last_at", renderText: time, width: 160 },
                  ]}
                />
              ),
            },
            {
              key: "events",
              label: t("行为流水", "Event stream"),
              children: (
                <DataTable
                  headerTitle={t("点击、加购、下单事件", "Click, cart and order events")}
                  actionRef={eventsRef}
                  params={{ region, days: 28 }}
                  request={tableRequest("/api/admin/site/events", { days: 28 })}
                  cardBordered={false}
                  columns={[
                    { title: t("关键词", "Keyword"), dataIndex: "q", hideInTable: true, filter: true, fieldProps: { placeholder: t("搜索路径、账号、来源或 IP", "Path, account, source or IP") } },
                    { title: t("事件类型", "Event"), dataIndex: "name", hideInTable: true, valueType: "select", valueEnum: Object.fromEntries(Object.entries(EVENTS).map(([k, v]) => [k, { text: v }])), filter: true },
                    { title: t("时间", "Time"), dataIndex: "at", renderText: time, width: 158 },
                    { title: t("事件", "Event"), dataIndex: "name", width: 100, render: (v) => EVENTS[v] || v },
                    { title: t("账号", "Account"), dataIndex: "account", width: 180, ellipsis: true, renderText: (v) => v || "—" },
                    { title: t("站点", "Site"), dataIndex: "region", width: 90, render: (_, row) => <RegionTag region={row.region} /> },
                    { title: t("路径", "Path"), dataIndex: "path", ellipsis: true },
                    { title: t("来源", "Source"), dataIndex: "source", width: 130, render: (v) => <SourceTag value={v} /> },
                    { title: t("设备", "Device"), dataIndex: "device", width: 140, ellipsis: true, render: (_, row) => deviceLabel(row.device, isEn) },
                    { title: t("IP（已打码）", "IP (masked)"), dataIndex: "ip", width: 130 },
                  ]}
                />
              ),
            },
          ]}
        />
      </ProCard>
    </PageContainer>
  );
}
