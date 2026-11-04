import { PageContainer, ProCard } from "@ant-design/pro-components";
import { Space, Tabs, Tag } from "antd";
import { useRef, useState } from "react";
import { SITE_REGIONS, tableRequest, time } from "../api";
import { DataTable, Kpis, LoadError, RegionSwitch, RegionTag, SourceTag, useLoad } from "../components";
import { api } from "../api";

const EVENTS = { pageview: "浏览", view_item: "看商品", add_to_cart: "加购", begin_checkout: "结账", purchase: "下单", signup: "注册", identify: "识别" };

export function VisitorsPage() {
  const [region, setRegion] = useState("all");
  const usersRef = useRef();
  const eventsRef = useRef();
  const summary = useLoad(() => api(`/api/admin/visitors/summary?region=${region}`), [region]);
  const s = summary.data || {};

  return (
    <PageContainer
      subTitle={`独立站访客、已识别账号与点击/下单行为（${SITE_REGIONS[region]}）`}
      extra={<RegionSwitch value={region} onChange={setRegion} />}
    >
      <LoadError error={summary.error} />
      <Kpis
        loading={summary.loading}
        cols={5}
        items={[
          { title: "访客", value: s.visitors, hint: `国内 ${s.cn ?? 0} · 海外 ${s.intl ?? 0}`, color: "#16a34a" },
          { title: "已识别账号", value: s.identified, hint: "带邮箱或用户 ID", color: "#0ea5e9" },
          { title: "新注册", value: s.signed_up, hint: "signup 事件", color: "#2563eb" },
          { title: "加过购物车", value: s.cart, hint: "至少一次加购", color: "#7c3aed" },
          { title: "完成下单", value: s.ordered, hint: "至少一笔订单", color: "#f59e0b" },
        ]}
      />
      <ProCard bordered bodyStyle={{ paddingTop: 4 }}>
        <Tabs
          items={[
            {
              key: "users",
              label: "已识别用户",
              children: (
                <DataTable
                  headerTitle="带账号的访客"
                  actionRef={usersRef}
                  params={{ region, identified: true, days: 90 }}
                  request={tableRequest("/api/admin/site/visitors", { identified: true, days: 90 })}
                  cardBordered={false}
                  columns={[
                    { title: "账号", dataIndex: "account" },
                    { title: "站点", dataIndex: "region", width: 90, render: (_, row) => <RegionTag region={row.region} /> },
                    { title: "来源", dataIndex: "source", render: (v) => <SourceTag value={v} /> },
                    { title: "浏览", dataIndex: "site_views", width: 70, align: "right" },
                    {
                      title: "行为",
                      render: (_, row) => (
                        <Space size={4}>
                          {row.added_cart && <Tag color="cyan">加购</Tag>}
                          {row.ordered && <Tag color="green">下单</Tag>}
                          {row.signed_up && <Tag>注册</Tag>}
                        </Space>
                      ),
                    },
                    { title: "最近", dataIndex: "last_at", renderText: time, width: 160 },
                  ]}
                />
              ),
            },
            {
              key: "events",
              label: "行为流水",
              children: (
                <DataTable
                  headerTitle="点击、加购、下单事件"
                  actionRef={eventsRef}
                  params={{ region, days: 28 }}
                  request={tableRequest("/api/admin/site/events", { days: 28 })}
                  cardBordered={false}
                  columns={[
                    { title: "时间", dataIndex: "at", renderText: time, width: 158 },
                    { title: "事件", dataIndex: "name", width: 88, render: (v) => EVENTS[v] || v },
                    { title: "账号", dataIndex: "account", width: 180, ellipsis: true, renderText: (v) => v || "—" },
                    { title: "站点", dataIndex: "region", width: 90, render: (_, row) => <RegionTag region={row.region} /> },
                    { title: "路径", dataIndex: "path", ellipsis: true },
                    { title: "来源", dataIndex: "source", width: 110, ellipsis: true },
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
