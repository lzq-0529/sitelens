import { PlusOutlined } from "@ant-design/icons";
import { ModalForm, PageContainer, ProCard, ProFormDigit, ProFormSelect, ProFormText, ProFormTextArea } from "@ant-design/pro-components";
import { App, Button, Col, Popconfirm, Row } from "antd";
import { useRef, useState } from "react";
import { api, money, tableRequest, time } from "../api";
import { useAuth } from "../auth";
import { DailyColumn, DataTable, DaysSwitch, Kpis, LoadError, RankTable, RegionTag, useLoad } from "../components";

const STATUS = { paid: { text: "已支付", status: "Success" }, refunded: { text: "已退款", status: "Error" } };
const CHANNELS = ["独立站收银台", "微信", "支付宝", "Stripe", "PayPal", "Shopify", "对公转账", "其他"];

export function OrdersPage() {
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
    <PageContainer subTitle="收入只统计已支付订单；转化看的是下单，不是试用点击" extra={<DaysSwitch value={days} onChange={setDays} options={[7, 30, 90]} />}>
      <LoadError error={summary.error} />
      <Kpis
        loading={summary.loading}
        cols={4}
        items={[
          { title: "本月收入", value: s ? money(s.month_cents) : "¥0.00", hint: "当月已支付", color: "#16a34a" },
          { title: `近 ${days} 天收入`, value: s ? money(s.d30_cents) : "¥0.00", badge: `${s?.orders_d30 ?? 0} 笔`, hint: "已扣除退款前的支付额", color: "#2563eb" },
          { title: "累计收入", value: s ? money(s.total_cents) : "¥0.00", hint: "历史已支付", color: "#7c3aed" },
          { title: "成交笔数", value: s?.orders_d30 ?? 0, hint: "近窗口已支付订单", color: "#f59e0b" },
        ]}
      />
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} xl={16}>
          <ProCard title="每日收入" bordered loading={summary.loading} className="sl-equal-card">
            <DailyColumn data={s?.daily} yField="cents" height={260} format={(cents) => money(cents)} />
          </ProCard>
        </Col>
        <Col xs={24} xl={8}>
            <RankTable title="按商品" height={260} rows={s?.by_product || s?.by_plan} columns={[{ title: "商品", dataIndex: "label" }, { title: "金额", dataIndex: "cents", align: "right", render: (cents) => money(cents) }]} />
        </Col>
      </Row>
      <DataTable
        headerTitle="订单列表"
        actionRef={tableRef}
        request={tableRequest("/api/admin/orders")}
        toolBarRender={() => (isOwner ? [<NewOrder key="new" onDone={changed} />] : [])}
        columns={[
          { title: "关键词", dataIndex: "q", hideInTable: true, filter: true, fieldProps: { placeholder: "客户、渠道、SKU 或商品" } },
          { title: "时间", dataIndex: "at", renderText: time, width: 160 },
          { title: "商品", dataIndex: "title", ellipsis: true },
          { title: "SKU", dataIndex: "sku", width: 120, renderText: (v) => v || "—" },
          { title: "区域", dataIndex: "region", width: 90, valueType: "select", valueEnum: { cn: { text: "国内" }, intl: { text: "海外" } }, filter: true, render: (_, row) => <RegionTag region={row.region} /> },
          { title: "金额", dataIndex: "amount_cents", align: "right", render: (_, row) => <b>{money(row.amount_cents, row.currency)}</b> },
          { title: "渠道", dataIndex: "channel" },
          { title: "状态", dataIndex: "status", valueType: "select", valueEnum: STATUS, filter: true },
          { title: "客户", dataIndex: "customer", ellipsis: true },
          {
            title: "操作",
            valueType: "option",
            hideInTable: !isOwner,
            render: (_, row) =>
              row.status === "paid"
                ? [
                    <Popconfirm
                      key="refund"
                      title="标记为已退款？"
                      onConfirm={async () => {
                        try {
                          await api(`/api/admin/orders/${row.id}/refund`, { method: "POST" });
                          message.success("已退款");
                          changed();
                        } catch (exc) {
                          message.error(exc.message);
                        }
                      }}
                    >
                      <a style={{ color: "#dc2626" }}>退款</a>
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
  const { message } = App.useApp();
  return (
    <ModalForm
      title="记一笔订单"
      width={480}
      trigger={<Button type="primary" icon={<PlusOutlined />}>记一笔订单</Button>}
      modalProps={{ destroyOnClose: true }}
      onFinish={async (values) => {
        try {
          await api("/api/admin/orders", { method: "POST", body: values });
          message.success("已记录");
          onDone();
          return true;
        } catch (exc) {
          message.error(exc.message);
          return false;
        }
      }}
    >
      <ProFormText name="title" label="商品" rules={[{ required: true }]} />
      <ProFormText name="sku" label="SKU" />
      <ProFormDigit name="amount" label="金额" min={0.01} rules={[{ required: true }]} fieldProps={{ precision: 2 }} />
      <ProFormSelect name="channel" label="渠道" options={CHANNELS.map((item) => ({ value: item, label: item }))} initialValue="独立站收银台" />
      <ProFormSelect name="region" label="站点" options={[{ value: "cn", label: "国内站" }, { value: "intl", label: "海外站" }]} initialValue="cn" />
      <ProFormText name="customer" label="客户" />
      <ProFormTextArea name="note" label="备注" />
    </ModalForm>
  );
}
