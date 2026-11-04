import { AuditOutlined, DashboardOutlined, GlobalOutlined, LogoutOutlined, MoneyCollectOutlined, SettingOutlined, TeamOutlined } from "@ant-design/icons";
import { PageLoading, ProLayout } from "@ant-design/pro-components";
import { Dropdown, Space, Tag } from "antd";
import { lazy, Suspense } from "react";
import { Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { BrandLogo, useAuth } from "./auth";
import { LangToggle, useLang, useT } from "./i18n";

const page = (load, name) => lazy(() => load().then((module) => ({ default: module[name] })));
const OverviewPage = page(() => import("./pages/overview"), "OverviewPage");
const SitePage = page(() => import("./pages/site"), "SitePage");
const VisitorsPage = page(() => import("./pages/visitors"), "VisitorsPage");
const OrdersPage = page(() => import("./pages/orders"), "OrdersPage");
const UsersPage = page(() => import("./pages/users"), "UsersPage");
const SettingsPage = page(() => import("./pages/settings"), "SettingsPage");

export function ConsoleLayout() {
  const t = useT();
  const { isEn } = useLang();
  const { user, logout, isOwner } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const ROUTES = [
    { path: "/overview", name: t("流量与总览", "Overview"), icon: <DashboardOutlined />, element: <OverviewPage /> },
    { path: "/site", name: t("站点 / SEO / GEO", "Site / SEO / GEO"), icon: <GlobalOutlined />, element: <SitePage /> },
    { path: "/visitors", name: t("网站用户与行为", "Visitors & behaviour"), icon: <TeamOutlined />, element: <VisitorsPage /> },
    { path: "/orders", name: t("订单与收入", "Orders & revenue"), icon: <MoneyCollectOutlined />, element: <OrdersPage /> },
    { path: "/settings", name: t("接入设置", "Setup"), icon: <SettingOutlined />, element: <SettingsPage /> },
    { path: "/users", name: t("后台账号与审计", "Accounts & audit"), icon: <AuditOutlined />, element: <UsersPage />, ownerOnly: true },
  ];
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
        <Space key="actions" size={10}>
          <Tag color="success" style={{ margin: 0 }}>
            {t("流量 · SEO · 下单 · GEO", "Traffic · SEO · Orders · GEO")}
          </Tag>
          <LangToggle />
        </Space>,
      ]}
      avatarProps={{
        title: `${isEn && user.display_name === "站点管理员" ? "Site owner" : user.display_name} (${isOwner ? t("管理员", "Owner") : t("只读", "Viewer")})`,
        size: "small",
        render: (_props, dom) => (
          <Dropdown menu={{ items: [{ key: "logout", icon: <LogoutOutlined />, label: t("退出登录", "Sign out"), onClick: logout }] }}>{dom}</Dropdown>
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
