import { PageContainer, ProCard } from "@ant-design/pro-components";
import { App, Button, Form, Input, Radio, Space, Typography } from "antd";
import { api } from "../api";
import { useAuth } from "../auth";
import { LoadError, useLoad } from "../components";

export function SettingsPage() {
  const { isOwner } = useAuth();
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const settings = useLoad(() => api("/api/admin/settings"), []);
  const data = settings.data || {};
  const origin = typeof window !== "undefined" ? window.location.origin : "http://127.0.0.1:8788";
  const snippet = `<script defer src="${origin}/tracker.js" data-region="cn"></script>`;

  return (
    <PageContainer subTitle="品牌、域名和 GEO 监测目标。这些会用来判断问答里有没有提到你的独立站。">
      <LoadError error={settings.error} />
      <Space direction="vertical" size={16} style={{ width: "100%" }}>
        <ProCard title="采集脚本" bordered>
          <Typography.Paragraph>把这段放到独立站页面。浏览会记 pageview；下单时调用 <Typography.Text code>sitelens.purchase({"{ amount: 199, sku: 'A1' }"})</Typography.Text>。</Typography.Paragraph>
          <Typography.Paragraph copyable={{ text: snippet }}>
            <pre style={{ background: "#f8fafc", padding: 12, borderRadius: 8 }}>{snippet}</pre>
          </Typography.Paragraph>
        </ProCard>
        <ProCard title="站点档案" bordered loading={settings.loading}>
          <Form
            form={form}
            layout="vertical"
            initialValues={{
              ...data,
              brand_aliases: (data.brand_aliases || []).join("\n"),
              domains: (data.domains || []).join("\n"),
              keywords: (data.keywords || []).join("\n"),
              competitors: (data.competitors || []).join("\n"),
              owned_urls: (data.owned_urls || []).join("\n"),
            }}
            key={data.brand}
            onFinish={async (values) => {
              try {
                await api("/api/admin/settings", { method: "PUT", body: values });
                message.success("已保存");
                settings.reload();
              } catch (exc) {
                message.error(exc.message);
              }
            }}
          >
            <Form.Item name="brand" label="品牌名" rules={[{ required: true }]}><Input /></Form.Item>
            <Form.Item name="category" label="品类"><Input placeholder="例如：家居、服饰、保健品" /></Form.Item>
            <Form.Item name="brand_aliases" label="品牌别名（每行一个）"><Input.TextArea rows={3} /></Form.Item>
            <Form.Item name="domains" label="官网域名（每行一个）"><Input.TextArea rows={3} /></Form.Item>
            <Form.Item name="keywords" label="希望被提到的关键词"><Input.TextArea rows={3} /></Form.Item>
            <Form.Item name="competitors" label="竞品名（出现在回答里会标出来）"><Input.TextArea rows={3} /></Form.Item>
            <Form.Item name="owned_urls" label="自有内容 URL"><Input.TextArea rows={3} /></Form.Item>
            <Form.Item name="geo_schedule" label="GEO 巡检节奏">
              <Radio.Group optionType="button" options={[{ value: "weekly", label: "每周（推荐，给 Grok / Muse）" }, { value: "daily", label: "每天" }]} />
            </Form.Item>
            {isOwner && <Button type="primary" htmlType="submit">保存</Button>}
          </Form>
        </ProCard>
        {data.ingest_token && (
          <ProCard title="Grok / Muse Token" bordered>
            <Typography.Paragraph copyable={{ text: data.ingest_token }}>{data.ingest_token}</Typography.Paragraph>
            <Typography.Text type="secondary">Agent 用这个 Token 拉 /api/geo/tasks，回传 /api/geo/ingest。默认按周巡检 15 家问答平台。</Typography.Text>
          </ProCard>
        )}
      </Space>
    </PageContainer>
  );
}
