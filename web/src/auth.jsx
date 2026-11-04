import { LockOutlined, SafetyCertificateOutlined, UserOutlined } from "@ant-design/icons";
import { App, Button, Form, Input, Spin } from "antd";
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api } from "./api";
import { LangToggle, useT } from "./i18n";

const AuthContext = createContext(null);

export function BrandLogo({ size = 36 }) {
  return (
    <span className="sl-brand-logo" aria-hidden="true">
      <svg viewBox="0 0 32 32" width={size} height={size}>
        <circle cx="14" cy="14" r="8.5" fill="none" stroke="#16a34a" strokeWidth="2.4" />
        <circle cx="14" cy="14" r="3.2" fill="#16a34a" />
        <path d="M20.6 20.6 28 28" stroke="#0f172a" strokeWidth="2.6" strokeLinecap="round" />
      </svg>
    </span>
  );
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    api("/api/admin/me").then(setUser).catch(() => setUser(null)).finally(() => setReady(true));
    const onSignedOut = () => setUser(null);
    window.addEventListener("sitelens:signed-out", onSignedOut);
    return () => window.removeEventListener("sitelens:signed-out", onSignedOut);
  }, []);

  const logout = useCallback(async () => {
    await api("/api/admin/logout", { method: "POST" }).catch(() => {});
    setUser(null);
  }, []);

  const value = useMemo(() => ({ user, setUser, logout, isOwner: user?.role === "owner" }), [user, logout]);
  if (!ready) return <Spin fullscreen />;
  return <AuthContext.Provider value={value}>{user ? children : <LoginPage onSignedIn={setUser} />}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}

function LoginPage({ onSignedIn }) {
  const t = useT();
  const { message } = App.useApp();
  const [submitting, setSubmitting] = useState(false);

  const handleFinish = async (values) => {
    setSubmitting(true);
    try {
      onSignedIn(await api("/api/admin/login", { method: "POST", body: values }));
    } catch (exc) {
      message.error(exc.message || t("登录失败", "Sign-in failed"));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="sl-login-shell">
      <div className="sl-login-card">
        <div className="sl-login-head">
          <div className="sl-login-brand">
            <BrandLogo size={40} />
            <span style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <span className="sl-login-badge">INDEPENDENT SITES</span>
              <LangToggle />
            </span>
          </div>
          <h1 className="sl-login-title">{t("SiteLens 独立站监控台", "SiteLens store ops console")}</h1>
          <p className="sl-login-subtitle">{t("流量 · SEO 抓取 · 下单转化 · GEO 问答", "Traffic · SEO crawlers · Checkout · GEO answers")}</p>
        </div>
        <Form layout="vertical" requiredMark={false} onFinish={handleFinish} className="sl-login-form">
          <Form.Item label={t("管理账号", "Admin account")} name="username" rules={[{ required: true, message: t("请输入用户名", "Enter username") }]}>
            <Input prefix={<UserOutlined className="sl-login-input-icon" />} placeholder={t("用户名", "Username")} />
          </Form.Item>
          <Form.Item label={t("密码", "Password")} name="password" rules={[{ required: true, message: t("请输入密码", "Enter password") }]}>
            <Input.Password prefix={<LockOutlined className="sl-login-input-icon" />} placeholder={t("密码", "Password")} />
          </Form.Item>
          <Button htmlType="submit" block loading={submitting} className="sl-login-submit">
            {t("进入监控台", "Open console")}
          </Button>
        </Form>
        <p className="sl-login-demo">
          {t("本地演示账号", "Local demo")} <code>owner</code> {t("密码", "password")} <code>sitelens-demo</code>
        </p>
        <div className="sl-login-foot">
          <SafetyCertificateOutlined />
          {t("后台不开放注册，不对外收录", "No public signup. Console is not indexed.")}
        </div>
      </div>
    </div>
  );
}
