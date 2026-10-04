"use strict";

const fs = require("fs");
const path = require("path");
const { execFile } = require("child_process");
const { promisify } = require("util");

const execFileAsync = promisify(execFile);

const API_ID = 2040;
const API_HASH = "b18441a1ff607e10a989891a5462e627";
const MARKETS = [
  { key: "mrkt", bots: ["mrkt"], shorts: ["app"] },
  { key: "portals", bots: ["portals"], shorts: ["market"] },
  { key: "tonnel", bots: ["tonnel_network_bot"], shorts: ["auction", "gift", "app"] },
];

const pending = new Map();
let telegramLib;

function explain(err) {
  const code = String((err && (err.errorMessage || err.message)) || err || "Ошибка");
  if (code.includes("PHONE_NUMBER_INVALID")) return "Номер неверный. Пиши его так: +79001234567";
  if (code.includes("PHONE_CODE_INVALID")) return "Неверный код из Telegram";
  if (code.includes("PHONE_CODE_EXPIRED")) return "Код устарел. Нажми «Получить код» ещё раз";
  if (code.includes("SESSION_PASSWORD_NEEDED")) return "Нужен облачный пароль 2FA";
  if (code.includes("FLOOD_WAIT")) return "Telegram просит подождать пару минут и попробовать снова";
  if (code.includes("PASSWORD_HASH_INVALID")) return "Неверный пароль 2FA";
  return code;
}

async function loadTelegram() {
  if (telegramLib) return telegramLib;
  try {
    telegramLib = require("telegram");
    return telegramLib;
  } catch {
    /* installed on first login if the image has no node_modules */
  }
  const dir = "/tmp/novice-mods";
  fs.mkdirSync(dir, { recursive: true });
  console.log("NOVICE installing telegram client");
  await execFileAsync(
    "npm",
    ["install", "--prefix", dir, "telegram@2.26.22", "--omit=dev", "--ignore-scripts"],
    { timeout: 180000 }
  );
  process.env.NODE_PATH = [path.join(dir, "node_modules"), process.env.NODE_PATH || ""]
    .filter(Boolean)
    .join(path.delimiter);
  require("module").Module._initPaths();
  telegramLib = require("telegram");
  return telegramLib;
}

async function startPhoneLogin(phone) {
  const number = String(phone || "").replace(/[^\d+]/g, "");
  if (!number.startsWith("+") || number.length < 8) {
    throw new Error("Номер неверный. Пиши его так: +79001234567");
  }
  const { TelegramClient } = await loadTelegram();
  const { StringSession } = require("telegram/sessions");
  const client = new TelegramClient(new StringSession(""), API_ID, API_HASH, {
    connectionRetries: 5,
    useWSS: true,
    timeout: 25,
  });
  if (typeof client.setLogLevel === "function") client.setLogLevel("error");
  await client.connect();
  let sent;
  try {
    sent = await client.sendCode({ apiId: API_ID, apiHash: API_HASH }, number);
  } catch (err) {
    await client.disconnect().catch(() => {});
    throw new Error(explain(err));
  }
  const loginId = `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 8)}`;
  pending.set(loginId, {
    client,
    phone: number,
    phoneCodeHash: sent.phoneCodeHash,
    created: Date.now(),
  });
  return { login_id: loginId, message: "Код отправлен в Telegram. Введи его ниже." };
}

async function confirmPhoneLogin(loginId, code, password) {
  const state = pending.get(loginId);
  if (!state) throw new Error("Сессия входа не найдена. Нажми «Получить код» ещё раз.");
  const { Api } = await loadTelegram();
  try {
    try {
      await state.client.invoke(
        new Api.auth.SignIn({
          phoneNumber: state.phone,
          phoneCodeHash: state.phoneCodeHash,
          phoneCode: String(code || "").trim(),
        })
      );
    } catch (err) {
      if (!String(err.errorMessage || err.message || "").includes("SESSION_PASSWORD_NEEDED")) {
        throw new Error(explain(err));
      }
      if (!password) throw new Error("Нужен облачный пароль 2FA");
      await state.client.signInWithPassword(
        { apiId: API_ID, apiHash: API_HASH },
        {
          password: async () => password,
          onError: async (err) => {
            throw err;
          },
        }
      );
    }
    const tokens = await fetchMarketTokens(state.client, Api);
    pending.delete(loginId);
    await state.client.disconnect().catch(() => {});
    return tokens;
  } catch (err) {
    const message = err && err.message ? err.message : "";
    if (/Номер|код|пароль|Telegram|Сессия|Не удалось/.test(message)) throw err;
    throw new Error(explain(err));
  }
}

async function fetchMarketTokens(client, Api) {
  const tokens = {};
  const errors = [];
  for (const market of MARKETS) {
    try {
      const initData = await initDataFor(client, Api, market);
      const token = await exchangeToken(market.key, initData);
      if (token) tokens[market.key] = token;
      else errors.push(market.key);
    } catch (err) {
      console.error("market auth", market.key, err && err.message ? err.message : err);
      errors.push(market.key);
    }
  }
  if (!Object.keys(tokens).length) {
    throw new Error("Не удалось открыть MRKT, Portals и Tonnel. Зайди в этих ботов в Telegram и повтори вход.");
  }
  return { tokens, connected: Object.keys(tokens), failed: errors };
}

async function initDataFor(client, Api, market) {
  let lastError;
  for (const botName of market.bots) {
    const entity = await client.getEntity(botName);
    for (const shortName of market.shorts) {
      try {
        const webView = await client.invoke(
          new Api.messages.RequestAppWebView({
            peer: entity,
            app: new Api.InputBotAppShortName({
              botId: new Api.InputUser({
                userId: entity.id,
                accessHash: entity.accessHash,
              }),
              shortName,
            }),
            platform: "android",
          })
        );
        const url = webView.url || "";
        const chunk = url.split("tgWebAppData=")[1];
        if (!chunk) throw new Error("no init data");
        return decodeURIComponent(chunk.split("&tgWebAppVersion")[0]);
      } catch (err) {
        lastError = err;
      }
    }
  }
  throw lastError || new Error("mini app not found");
}

async function exchangeToken(market, initData) {
  if (market === "mrkt") {
    const res = await fetch("https://api.tgmrkt.io/api/v1/auth", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ data: initData }),
    });
    const data = await res.json().catch(() => ({}));
    return data.token || "";
  }
  if (market === "portals") return `tma ${initData}`;
  if (market === "tonnel") return initData;
  return "";
}

module.exports = { startPhoneLogin, confirmPhoneLogin };
