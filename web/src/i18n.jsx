import { Segmented } from "antd";
import { createContext, useContext, useEffect, useMemo, useState } from "react";

const LangContext = createContext(null);
const KEY = "sitelens-lang";

export function LangProvider({ children }) {
  const [lang, setLang] = useState(() => {
    try {
      return window.localStorage.getItem(KEY) === "en" ? "en" : "zh";
    } catch {
      return "zh";
    }
  });
  useEffect(() => {
    try {
      window.localStorage.setItem(KEY, lang);
    } catch {}
    document.documentElement.lang = lang === "en" ? "en" : "zh-CN";
  }, [lang]);
  const value = useMemo(() => ({ lang, setLang, isEn: lang === "en" }), [lang]);
  return <LangContext.Provider value={value}>{children}</LangContext.Provider>;
}

export function useLang() {
  const ctx = useContext(LangContext);
  if (!ctx) return { lang: "zh", setLang: () => {}, isEn: false };
  return ctx;
}

/** t("访客", "Visitors") — inline bilingual string picker. */
export function useT() {
  const { isEn } = useLang();
  return (zh, en) => (isEn ? en : zh);
}

export function LangToggle() {
  const { lang, setLang } = useLang();
  return (
    <Segmented
      size="small"
      value={lang}
      onChange={setLang}
      options={[
        { value: "zh", label: "中文" },
        { value: "en", label: "EN" },
      ]}
    />
  );
}

const SOURCE_EN = {
  直接访问: "Direct",
  知乎: "Zhihu",
  小红书: "Xiaohongshu",
  微信: "WeChat",
  抖音: "Douyin",
  快手: "Kuaishou",
  B站: "Bilibili",
  微博: "Weibo",
  头条: "Toutiao",
  飞书: "Feishu",
  钉钉: "DingTalk",
  掘金: "Juejin",
  少数派: "SSPAI",
  豆瓣: "Douban",
  雪球: "Xueqiu",
  百度: "Baidu",
  夸克: "Quark",
  搜狗: "Sogou",
  神马: "Shenma",
  "360搜索": "360 Search",
  花瓣: "Petal",
  未知爬虫: "Unknown crawler",
  "头条/抖音": "Toutiao / Douyin",
};

const ENGINE_EN = {
  百度: "Baidu",
  "头条/抖音": "Toutiao / Douyin",
  搜狗: "Sogou",
  花瓣: "Petal",
  神马: "Shenma",
  未识别: "Unknown",
  未知爬虫: "Unknown crawler",
  通义千问: "Tongyi Qianwen",
  "DeepSeek 网页": "DeepSeek",
  豆包: "Doubao",
  文心一言: "Wenxin Yiyan",
  智谱清言: "ChatGLM",
  腾讯元宝: "Tencent Yuanbao",
  "秘塔 AI": "Metaso AI",
  天工: "Tiangong",
  国内: "China",
  海外: "International",
  每周: "Weekly",
  每天: "Daily",
  是: "Yes",
  待测: "Pending",
};

export function localise(value, isEn, table) {
  const text = String(value ?? "");
  if (!isEn) return text;
  return table[text] || text;
}

export function sourceLabel(value, isEn) {
  return localise(value || "直接访问", isEn, SOURCE_EN);
}

export function engineLabel(value, isEn) {
  return localise(value, isEn, ENGINE_EN);
}

export function deviceLabel(value, isEn) {
  const text = String(value || "");
  if (!isEn) return text;
  return text
    .replace("未知设备", "Unknown device")
    .replace("手机", "Mobile")
    .replace("平板", "Tablet");
}
