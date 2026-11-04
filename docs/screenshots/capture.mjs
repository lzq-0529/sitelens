import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

const BASE = process.env.SITELENS_URL || "http://127.0.0.1:8788";
const PORT = Number(process.env.SITELENS_CDP_PORT || 9334);
const OUT = path.resolve(import.meta.dirname);
const PROFILE = path.join(OUT, ".chrome-profile");
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

fs.mkdirSync(OUT, { recursive: true });
fs.rmSync(PROFILE, { recursive: true, force: true });

const chrome = spawn(
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  [
    "--headless=new",
    `--remote-debugging-port=${PORT}`,
    `--user-data-dir=${PROFILE}`,
    "--window-size=1440,900",
    "--no-first-run",
    "--no-default-browser-check",
    "--hide-scrollbars",
    "--font-render-hinting=none",
    "about:blank",
  ],
  { stdio: "ignore" },
);

async function waitDebugger() {
  for (let i = 0; i < 60; i += 1) {
    try {
      const list = await fetch(`http://127.0.0.1:${PORT}/json/list`).then((r) => r.json());
      const page = list.find((item) => item.type === "page");
      if (page) return page;
    } catch {}
    await sleep(250);
  }
  throw new Error("Chrome debugger not ready");
}

const target = await waitDebugger();
const ws = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((resolve, reject) => {
  ws.onopen = resolve;
  ws.onerror = reject;
});

let seq = 0;
const pending = new Map();
ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  if (message.id && pending.has(message.id)) {
    const { resolve, reject } = pending.get(message.id);
    pending.delete(message.id);
    message.error ? reject(new Error(JSON.stringify(message.error))) : resolve(message.result);
  }
};

function cmd(method, params = {}) {
  const id = ++seq;
  return new Promise((resolve, reject) => {
    pending.set(id, { resolve, reject });
    ws.send(JSON.stringify({ id, method, params }));
    setTimeout(() => {
      if (pending.has(id)) {
        pending.delete(id);
        reject(new Error(`timeout ${method}`));
      }
    }, 25000);
  });
}

async function ev(expression) {
  const result = await cmd("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true });
  if (result.exceptionDetails) {
    throw new Error(result.exceptionDetails.text || "evaluate failed");
  }
  return result.result.value;
}

async function waitReady() {
  for (let i = 0; i < 20; i += 1) {
    const state = await ev(`(async () => {
      await document.fonts.ready;
      const noto = [...document.fonts].some((f) => f.family.includes("Noto Sans SC") && f.status === "loaded");
      const canvas = document.createElement("canvas").getContext("2d");
      canvas.font = '24px "Noto Sans SC"';
      const width = canvas.measureText("监控台").width;
      return { ready: document.readyState, noto, width, text: (document.body.innerText || "").slice(0, 80) };
    })()`);
    if (state.ready === "complete" && state.noto && state.width > 40) return state;
    await sleep(400);
  }
  return ev(`({ ready: document.readyState, fonts: [...document.fonts].map(f => f.family + ':' + f.status).slice(0, 12), text: (document.body.innerText || "").slice(0, 120) })`);
}

async function nav(urlPath) {
  await cmd("Page.navigate", { url: BASE + urlPath });
  await sleep(1200);
  const fonts = await waitReady();
  await sleep(1800);
  return fonts;
}

async function shot(name) {
  const result = await cmd("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
  const file = path.join(OUT, `${name}.png`);
  fs.writeFileSync(file, Buffer.from(result.data, "base64"));
  console.log("wrote", file, fs.statSync(file).size);
}

async function clickTab(label) {
  return ev(`(() => {
    const tab = [...document.querySelectorAll(".ant-tabs-tab")].find((el) => el.innerText.includes(${JSON.stringify(label)}));
    if (!tab) return false;
    tab.scrollIntoView();
    tab.click();
    return true;
  })()`);
}

try {
  await cmd("Page.enable");
  await cmd("Runtime.enable");
  await cmd("Emulation.setDeviceMetricsOverride", { width: 1440, height: 900, deviceScaleFactor: 2, mobile: false });

  const loginFonts = await nav("/overview");
  console.log("login", loginFonts);
  await shot("login");
  await ev(`(() => {
    const set = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
    const inputs = document.querySelectorAll("input");
    set.call(inputs[0], "owner");
    inputs[0].dispatchEvent(new Event("input", { bubbles: true }));
    set.call(inputs[1], "sitelens-demo");
    inputs[1].dispatchEvent(new Event("input", { bubbles: true }));
    const button = [...document.querySelectorAll("button")].find((el) => el.innerText.includes("进入监控台"));
    button?.click();
    return !!button;
  })()`);
  await sleep(3500);

  console.log("overview", await nav("/overview"));
  await shot("overview");

  console.log("site", await nav("/site"));
  await shot("site");
  console.log("seo tab", await clickTab("搜索引擎与 AI 抓取"));
  await sleep(2200);
  await shot("seo");
  console.log("geo tab", await clickTab("AI 回答引用监测"));
  await sleep(2200);
  await shot("geo");

  console.log("visitors", await nav("/visitors"));
  await shot("visitors");
  console.log("orders", await nav("/orders"));
  await shot("orders");
  console.log("settings", await nav("/settings"));
  await shot("settings");
} finally {
  ws.close();
  chrome.kill("SIGTERM");
  fs.rmSync(PROFILE, { recursive: true, force: true });
}
