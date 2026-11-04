import { App as AntApp, ConfigProvider } from "antd";
import enUS from "antd/locale/en_US";
import zhCN from "antd/locale/zh_CN";
import dayjs from "dayjs";
import "dayjs/locale/en";
import "dayjs/locale/zh-cn";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { AuthProvider } from "./auth";
import { LangProvider, useLang } from "./i18n";
import "./sitelens.css";
import { ConsoleLayout } from "./layout";

function Shell() {
  const { isEn } = useLang();
  dayjs.locale(isEn ? "en" : "zh-cn");
  return (
    <ConfigProvider
      locale={isEn ? enUS : zhCN}
      theme={{
        token: {
          colorPrimary: "#16a34a",
          borderRadius: 10,
          colorBgContainer: "#ffffff",
          fontFamily: '-apple-system, BlinkMacSystemFont, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", Inter, sans-serif',
        },
      }}
    >
      <AntApp>
        <BrowserRouter>
          <AuthProvider>
            <ConsoleLayout />
          </AuthProvider>
        </BrowserRouter>
      </AntApp>
    </ConfigProvider>
  );
}

createRoot(document.getElementById("root")).render(
  <LangProvider>
    <Shell />
  </LangProvider>,
);
