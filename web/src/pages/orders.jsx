import { PlusOutlined } from "@ant-design/icons";
import { ModalForm, PageContainer, ProCard, ProFormDigit, ProFormSelect, ProFormText, ProFormTextArea } from "@ant-design/pro-components";
import { App, Button, Col, Popconfirm, Row } from "antd";
import { useRef, useState } from "react";
import { api, money, tableRequest, time } from "../api";
import { useAuth } from "../auth";
import { DailyColumn, DataTable, DaysSwitch, Kpis, LoadError, RankTable, RegionTag, useLoad } from "../components";
import { useLang, useT } from "../i18n";

const CHANNELS = ["独立站收银台", "微信", "支付宝", "Stripe", "PayPal", "Shopify", "对公转账", "其他"];

const PRODUCT_EN = { "亚麻床品四件套": "Linen bedding set", "北岛羊毛毯": "North Island wool throw", "手冲咖啡套装": "Pour-over coffee set" };

export function OrdersPage() {
  const t = useT();
  const { isEn } = useLang();
  const product = (name) => (isEn ? PRODUCT_EN[name] || name : name);
  const STATUS = { paid: { text: t("已支付", "Paid") }, refunded: { text: t("已退款", "Refunded") } };
  const { isOwner } = useAuth();
  const { message } = App.useApp();
  const tableRef = useRef();
  const [days, setDays] = useState(30);
  const summary = useLoad(() => api(`/api/admin/orders/summary?days=${days}`), [days]);
  const s = summary.data;
  const changed = () => {
    tableRef.current?.reload();
    summary.reload();
  };

  return (
    <PageContainer subTitle={t("收入只统计已支付订单；转化看的是下单，不是试用点击", "Revenue counts paid orders only; conversion means orders, not trial clicks")} extra={<DaysSwitch value={days} onChange={setDays} options={[7, 30, 90]} />}>
      <LoadError error={summary.error} />
      <Kpis
        loading={summary.loading}
        cols={5}
        items={[
          { title: t("本月收入", "Revenue this month"), value: s ? money(s.month_cents) : "¥0.00", hint: t("当月已支付", "Paid this month"), color: "#16a34a" },
          { title: t(`近 ${days} 天收入`, `Revenue, last ${days}d`), value: s ? money(s.d30_cents) : "¥0.00", badge: t(`${s?.orders_d30 ?? 0} 笔`, `${s?.orders_d30 ?? 0} orders`), hint: t("已支付额", "Paid total"), color: "#2563eb" },
          { title: t("累计收入", "All-time revenue"), value: s ? money(s.total_cents) : "¥0.00", hint: t("历史已支付", "All paid"), color: "#7c3aed" },
          { title: t("客单价", "Avg order value"), value: s ? money(s.aov_cents) : "¥0.00", hint: t("近窗口平均每笔", "Per paid order in window"), color: "#0ea5e9" },
          { title: t("成交笔数", "Paid orders"), value: s?.orders_d30 ?? 0, hint: t(`复购客户 ${s?.repeat_customers ?? 0} · 退款 ${s?.refunded ?? 0}`, `Repeat buyers ${s?.repeat_customers ?? 0} · Refunds ${s?.refunded ?? 0}`), color: "#f59e0b" },
        ]}
      />
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} xl={16}>
          <ProCard title={t("每日收入", "Daily revenue")} bordered loading={summary.loading} className="sl-equal-card">
            <DailyColumn data={s?.daily} yField="cents" height={260} format={(cents) => money(cents)} />
          </ProCard>
        </Col>
        <Col xs={24} xl={8}>
            <RankTable title={t("按商品", "By product")} height={260} rows={s?.by_product || s?.by_plan} columns={[{ title: t("商品", "Product"), dataIndex: "label", render: (v) => product(v) }, { title: t("金额", "Amount"), dataIndex: "cents", align: "right", render: (cents) => money(cents) }]} />
        </Col>
      </Row>
      <DataTable
        headerTitle={t("订单列表", "Orders")}
        actionRef={tableRef}
        request={tableRequest("/api/admin/orders")}
        toolBarRender={() => (isOwner ? [<NewOrder key="new" onDone={changed} />] : [])}
        columns={[
          { title: t("关键词", "Keyword"), dataIndex: "q", hideInTable: true, filter: true, fieldProps: { placeholder: t("客户、渠道、SKU 或商品", "Customer, channel, SKU or product") } },
          { title: t("时间", "Time"), dataIndex: "at", renderText: time, width: 160 },
          { title: t("商品", "Product"), dataIndex: "title", ellipsis: true, render: (_, row) => product(row.title) },
          { title: "SKU", dataIndex: "sku", width: 120, renderText: (v) => v || "—" },
          { title: t("区域", "Region"), dataIndex: "region", width: 90, valueType: "select", valueEnum: { cn: { text: t("国内", "China") }, intl: { text: t("海外", "Intl") } }, filter: true, render: (_, row) => <RegionTag region={row.region} /> },
          { title: t("金额", "Amount"), dataIndex: "amount_cents", align: "right", render: (_, row) => <b>{money(row.amount_cents, row.currency)}</b> },
          { title: t("渠道", "Channel"), dataIndex: "channel" },
          { title: t("状态", "Status"), dataIndex: "status", valueType: "select", valueEnum: STATUS, filter: true, render: (_, row) => (row.status === "paid" ? t("已支付", "Paid") : t("已退款", "Refunded")) },
          { title: t("客户", "Customer"), dataIndex: "customer", ellipsis: true },
          {
            title: t("操作", "Action"),
            valueType: "option",
            hideInTable: !isOwner,
            render: (_, row) =>
              row.status === "paid"
                ? [
                    <Popconfirm
                      key="refund"
                      title={t("标记为已退款？", "Mark as refunded?")}
                      onConfirm={async () => {
                        try {
                          await api(`/api/admin/orders/${row.id}/refund`, { method: "POST" });
                          message.success(t("已退款", "Refunded"));
                          changed();
                        } catch (exc) {
                          message.error(exc.message);
                        }
                      }}
                    >
                      <a style={{ color: "#dc2626" }}>{t("退款", "Refund")}</a>
                    </Popconfirm>,
                  ]
                : [],
          },
        ]}
      />
    </PageContainer>
  );
}

function NewOrder({ onDone }) {
  const t = useT();
  const { message } = App.useApp();
  return (
    <ModalForm
      title={t("记一笔订单", "Record an order")}
      width={480}
      trigger={<Button type="primary" icon={<PlusOutlined />}>{t("记一笔订单", "Record order")}</Button>}
      modalProps={{ destroyOnClose: true }}
      onFinish={async (values) => {
        try {
          await api("/api/admin/orders", { method: "POST", body: values });
          message.success(t("已记录", "Recorded"));
          onDone();
          return true;
        } catch (exc) {
          message.error(exc.message);
          return false;
        }
      }}
    >
      <ProFormText name="title" label={t("商品", "Product")} rules={[{ required: true }]} />
      <ProFormText name="sku" label="SKU" />
      <ProFormDigit name="amount" label={t("金额", "Amount")} min={0.01} rules={[{ required: true }]} fieldProps={{ precision: 2 }} />
      <ProFormSelect name="channel" label={t("渠道", "Channel")} options={CHANNELS.map((item) => ({ value: item, label: item }))} initialValue="独立站收银台" />
      <ProFormSelect name="region" label={t("站点", "Site")} options={[{ value: "cn", label: t("国内站", "China") }, { value: "intl", label: t("海外站", "International") }]} initialValue="cn" />
      <ProFormText name="customer" label={t("客户", "Customer")} />
      <ProFormTextArea name="note" label={t("备注", "Note")} />
    </ModalForm>
  );
}
