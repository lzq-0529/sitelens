import { App as AntApp, ConfigProvider } from "antd";
import zhCN from "antd/locale/zh_CN";
import dayjs from "dayjs";
import "dayjs/locale/zh-cn";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { AuthProvider } from "./auth";
import "./sitelens.css";
import { ConsoleLayout } from "./layout";

dayjs.locale("zh-cn");

createRoot(document.getElementById("root")).render(
  <ConfigProvider
    locale={zhCN}
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
  </ConfigProvider>,
);
