import { PlusOutlined } from "@ant-design/icons";
import { ModalForm, PageContainer, ProCard, ProFormRadio, ProFormText } from "@ant-design/pro-components";
import { App, Button, Popconfirm, Tabs, Tag } from "antd";
import { useRef, useState } from "react";
import { api, tableRequest, time } from "../api";
import { useAuth } from "../auth";
import { DataTable } from "../components";

const ROLES = { owner: "管理员", viewer: "只读" };
const ACTIONS = {
  login: "登录",
  create_order: "记录订单",
  refund_order: "订单退款",
  create_user: "新建账号",
  edit_user: "修改账号",
  geo_ingest: "录入 GEO 结果",
  geo_prompts: "修改 GEO 提问词",
  update_settings: "修改站点设置",
  create_owner_cli: "命令行创建管理员",
  reset_password_cli: "命令行重设密码",
};

export function UsersPage() {
  return (
    <PageContainer subTitle="后台不开放注册：管理员在这里建号。只读账号能看流量、下单和 GEO，不能改。">
      <ProCard bordered bodyStyle={{ paddingTop: 4 }}>
        <Tabs items={[{ key: "users", label: "账号", children: <UserTable /> }, { key: "audit", label: "操作记录", children: <AuditTable /> }]} />
      </ProCard>
    </PageContainer>
  );
}

function UserTable() {
  const { user: me } = useAuth();
  const { message } = App.useApp();
  const tableRef = useRef();
  const [resetting, setResetting] = useState(null);

  async function patch(row, body, done = "已更新") {
    try {
      await api(`/api/admin/users/${row.id}`, { method: "PATCH", body });
      message.success(done);
      tableRef.current?.reload();
      return true;
    } catch (exc) {
      message.error(exc.message);
      return false;
    }
  }

  return (
    <DataTable
      headerTitle="账号"
      actionRef={tableRef}
      cardBordered={false}
      request={tableRequest("/api/admin/users")}
      toolBarRender={() => [
        <ModalForm
          key="new"
          title="新建账号"
          width={460}
          trigger={<Button type="primary" icon={<PlusOutlined />}>新建账号</Button>}
          modalProps={{ destroyOnClose: true }}
          initialValues={{ role: "viewer" }}
          onFinish={async (values) => {
            try {
              await api("/api/admin/users", { method: "POST", body: values });
              message.success("已创建");
              tableRef.current?.reload();
              return true;
            } catch (exc) {
              message.error(exc.message);
              return false;
            }
          }}
        >
          <ProFormText name="username" label="用户名" rules={[{ required: true }]} />
          <ProFormText name="display_name" label="显示名" />
          <ProFormText.Password name="password" label="初始密码" rules={[{ required: true }, { min: 10 }]} />
          <ProFormRadio.Group name="role" label="角色" radioType="button" valueEnum={ROLES} />
        </ModalForm>,
      ]}
      columns={[
        { title: "用户名", dataIndex: "username", render: (_, row) => <>{row.username}{row.id === me.id && <Tag style={{ marginLeft: 8 }}>我</Tag>}</> },
        { title: "显示名", dataIndex: "display_name" },
        { title: "角色", dataIndex: "role", render: (v) => ROLES[v] || v },
        { title: "状态", dataIndex: "disabled", render: (v) => (v ? <Tag color="red">停用</Tag> : <Tag color="green">正常</Tag>) },
        { title: "最近登录", dataIndex: "last_login_at", renderText: time },
        {
          title: "操作",
          valueType: "option",
          render: (_, row) => [
            <a key="reset" onClick={() => setResetting(row)}>重置密码</a>,
            row.id !== me.id && (
              <Popconfirm key="ban" title={row.disabled ? "恢复此账号？" : "停用此账号？"} onConfirm={() => patch(row, { disabled: !row.disabled })}>
                <a>{row.disabled ? "恢复" : "停用"}</a>
              </Popconfirm>
            ),
          ],
        },
      ]}
    >
      <ModalForm
        title="重置密码"
        open={Boolean(resetting)}
        onOpenChange={(open) => !open && setResetting(null)}
        onFinish={async (values) => patch(resetting, { password: values.password }, "已重置密码")}
      >
        <ProFormText.Password name="password" label="新密码" rules={[{ required: true }, { min: 10 }]} />
      </ModalForm>
    </DataTable>
  );
}

function AuditTable() {
  return (
    <DataTable
      headerTitle="操作记录"
      cardBordered={false}
      request={tableRequest("/api/admin/audit")}
      columns={[
        { title: "时间", dataIndex: "at", renderText: time, width: 170 },
        { title: "动作", dataIndex: "action", render: (v) => ACTIONS[v] || v },
        { title: "详情", dataIndex: "detail", ellipsis: true },
      ]}
    />
  );
}
