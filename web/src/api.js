import dayjs from "dayjs";

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

export async function api(path, { method = "GET", body } = {}) {
  const response = await fetch(path, {
    method,
    credentials: "same-origin",
    headers: body === undefined ? {} : { "content-type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await response.json().catch(() => ({}));
  if (response.status === 401 && path !== "/api/admin/login") {
    window.dispatchEvent(new CustomEvent("sitelens:signed-out"));
  }
  if (!response.ok) throw new ApiError(data.error || `请求失败（${response.status}）`, response.status);
  return data;
}

export function query(params) {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params || {})) {
    if (value === undefined || value === null || value === "") continue;
    search.set(key, String(value));
  }
  const text = search.toString();
  return text ? `?${text}` : "";
}

export function tableRequest(path, extra = {}) {
  return async (params) => {
    const { current, pageSize, ...filters } = params;
    try {
      return await api(`${path}${query({ current, pageSize, ...extra, ...filters })}`);
    } catch (exc) {
      return { data: [], total: 0, success: false, errorMessage: exc.message };
    }
  };
}

export const money = (cents, currency = "CNY") => {
  const symbol = currency === "USD" ? "$" : currency === "CNY" || !currency ? "¥" : `${currency} `;
  return `${symbol}${((cents || 0) / 100).toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
};
export const time = (iso) => (iso ? dayjs(iso).format("YYYY-MM-DD HH:mm") : "—");
export const pct = (part, whole) => (whole ? `${Math.round((part / whole) * 100)}%` : "0%");
export const SITE_REGIONS = { all: "全球汇总", cn: "国内站", intl: "海外站" };
export const enumOf = (map) => Object.fromEntries(Object.entries(map).map(([key, text]) => [key, { text }]));
