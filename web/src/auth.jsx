import { LockOutlined, SafetyCertificateOutlined, UserOutlined } from "@ant-design/icons";
import { App, Button, Form, Input, Spin } from "antd";
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api } from "./api";

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
  if (!ready) return <Spin fullscreen tip="正在加载…" />;
  return <AuthContext.Provider value={value}>{user ? children : <LoginPage onSignedIn={setUser} />}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}

function LoginPage({ onSignedIn }) {
  const { message } = App.useApp();
  const [submitting, setSubmitting] = useState(false);

  const handleFinish = async (values) => {
    setSubmitting(true);
    try {
      onSignedIn(await api("/api/admin/login", { method: "POST", body: values }));
    } catch (exc) {
      message.error(exc.message || "登录失败");
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
            <span className="sl-login-badge">INDEPENDENT SITES</span>
          </div>
          <h1 className="sl-login-title">SiteLens 独立站监控台</h1>
          <p className="sl-login-subtitle">流量分析 · 下单转化 · GEO 问答监测</p>
        </div>
        <Form layout="vertical" requiredMark={false} onFinish={handleFinish} className="sl-login-form">
          <Form.Item label="管理账号" name="username" rules={[{ required: true, message: "请输入用户名" }]}>
            <Input prefix={<UserOutlined className="sl-login-input-icon" />} placeholder="用户名" />
          </Form.Item>
          <Form.Item label="密码" name="password" rules={[{ required: true, message: "请输入密码" }]}>
            <Input.Password prefix={<LockOutlined className="sl-login-input-icon" />} placeholder="密码" />
          </Form.Item>
          <Button htmlType="submit" block loading={submitting} className="sl-login-submit">
            进入监控台
          </Button>
        </Form>
        <div className="sl-login-foot">
          <SafetyCertificateOutlined />
          后台不开放注册，不对外收录
        </div>
      </div>
    </div>
  );
}
