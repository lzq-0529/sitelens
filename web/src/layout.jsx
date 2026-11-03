import { AuditOutlined, DashboardOutlined, GlobalOutlined, LogoutOutlined, MoneyCollectOutlined, SettingOutlined, TeamOutlined } from "@ant-design/icons";
import { PageLoading, ProLayout } from "@ant-design/pro-components";
import { Dropdown, Tag } from "antd";
import { lazy, Suspense } from "react";
import { Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { BrandLogo, useAuth } from "./auth";

const page = (load, name) => lazy(() => load().then((module) => ({ default: module[name] })));
const OverviewPage = page(() => import("./pages/overview"), "OverviewPage");
const SitePage = page(() => import("./pages/site"), "SitePage");
const VisitorsPage = page(() => import("./pages/visitors"), "VisitorsPage");
const OrdersPage = page(() => import("./pages/orders"), "OrdersPage");
const UsersPage = page(() => import("./pages/users"), "UsersPage");
const SettingsPage = page(() => import("./pages/settings"), "SettingsPage");

const ROUTES = [
  { path: "/overview", name: "流量与总览", icon: <DashboardOutlined />, element: <OverviewPage /> },
  { path: "/site", name: "国内外站点分析", icon: <GlobalOutlined />, element: <SitePage /> },
  { path: "/visitors", name: "网站用户与行为", icon: <TeamOutlined />, element: <VisitorsPage /> },
  { path: "/orders", name: "订单与收入", icon: <MoneyCollectOutlined />, element: <OrdersPage /> },
  { path: "/settings", name: "站点与 GEO 接入", icon: <SettingOutlined />, element: <SettingsPage /> },
  { path: "/users", name: "后台账号与审计", icon: <AuditOutlined />, element: <UsersPage />, ownerOnly: true },
];

export function ConsoleLayout() {
  const { user, logout, isOwner } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const routes = ROUTES.filter((route) => !route.ownerOnly || isOwner);
  return (
    <ProLayout
      title="SiteLens"
      logo={<BrandLogo size={26} />}
      layout="mix"
      fixSiderbar
      fixedHeader
      siderWidth={216}
      location={{ pathname: location.pathname }}
      route={{ path: "/", routes: routes.map(({ path, name, icon }) => ({ path, name, icon })) }}
      menuItemRender={(item, dom) => <a onClick={() => navigate(item.path)}>{dom}</a>}
      actionsRender={() => [
        <Tag key="env" color="success" style={{ margin: 0 }}>
          独立站流量 · 下单 · GEO
        </Tag>,
      ]}
      avatarProps={{
        title: `${user.display_name}（${isOwner ? "管理员" : "只读"}）`,
        size: "small",
        render: (_props, dom) => (
          <Dropdown menu={{ items: [{ key: "logout", icon: <LogoutOutlined />, label: "退出登录", onClick: logout }] }}>{dom}</Dropdown>
        ),
      }}
      token={{
        header: { colorBgHeader: "#0f172a", colorHeaderTitle: "#fff", colorTextRightActionsItem: "#e5e7eb" },
        sider: { colorMenuBackground: "#ffffff", colorTextMenuSelected: "#16a34a", colorBgMenuItemSelected: "#f0fdf4" },
      }}
    >
      <Suspense fallback={<PageLoading />}>
        <Routes>
          <Route path="/" element={<Navigate to="/overview" replace />} />
          {routes.map((route) => (
            <Route key={route.path} path={route.path} element={route.element} />
          ))}
          <Route path="*" element={<Navigate to="/overview" replace />} />
        </Routes>
      </Suspense>
    </ProLayout>
  );
}
