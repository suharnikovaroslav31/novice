// Bothost starts this file with Node. The .py name is the panel entrypoint.
"use strict";

console.log("NOVICE boot");

const http = require("http");
const fs = require("fs");
const path = require("path");
const { URL } = require("url");
const { accountStatus, getTokens, saveTokens } = require("./lib/store");
const { startPhoneLogin, confirmPhoneLogin } = require("./lib/phone");
const { searchMarkets } = require("./lib/search");

const PORT = Number(process.env.PORT || 8000);
const WEB = path.join(__dirname, "web");
const TOKEN =
  process.env.BOT_TOKEN ||
  process.env.TELEGRAM_BOT_TOKEN ||
  process.env.API_TOKEN ||
  "";

const GIFTS = [
  ["Desk Calendar", "📅", "#9BE7C8", "#FFE1D2"],
  ["Lol Pop", "🍭", "#FFB4C8", "#D8FF3F"],
  ["Homemade Cake", "🎂", "#FFD9A8", "#C9F7B4"],
  ["Spiced Wine", "🍷", "#E8B0C8", "#B8FFE4"],
  ["Eternal Rose", "🌹", "#FFB3A8", "#F7E8B0"],
  ["Delicious Cake", "🧁", "#FFD0E0", "#C8F0FF"],
  ["Green Star", "⭐", "#D8FF3F", "#9BE7C8"],
  ["Crystal Ball", "🔮", "#C8D8FF", "#E8C8FF"],
];
const MODELS = ["Default", "Gold", "Neon", "Midnight", "Pearl"];
const BACKDROPS = ["Black", "Ivory", "Sky", "Burgundy", "Mint"];

function publicBase() {
  const domain = (process.env.DOMAIN || "").trim();
  if (domain && domain !== "Значение") {
    return domain.startsWith("http") ? domain.replace(/\/$/, "") : `https://${domain.replace(/\/$/, "")}`;
  }
  const webhook = (process.env.WEBHOOK_URL || "").trim();
  if (webhook.startsWith("https://")) return webhook.split("/webhook")[0];
  return "https://bot-1791107545-9749-suharnikovaroslav31.bothost.tech";
}

function svg(name, emoji, c1, c2) {
  const xml = `<svg xmlns='http://www.w3.org/2000/svg' width='512' height='512' viewBox='0 0 512 512'><defs><linearGradient id='g' x1='0' y1='0' x2='1' y2='1'><stop offset='0%' stop-color='${c1}'/><stop offset='100%' stop-color='${c2}'/></linearGradient></defs><rect width='512' height='512' rx='96' fill='url(#g)'/><text x='256' y='280' text-anchor='middle' font-size='150'>${emoji}</text><text x='256' y='390' text-anchor='middle' font-family='Arial' font-size='28' font-weight='700' fill='#101812'>${name}</text></svg>`;
  return "data:image/svg+xml;charset=utf-8," + encodeURIComponent(xml);
}

function demoItems() {
  const items = [];
  for (let i = 0; i < 24; i++) {
    const [name, emoji, c1, c2] = GIFTS[i % GIFTS.length];
    const price = Math.round((0.9 + ((i * 37) % 110) / 10) * 100) / 100;
    items.push({
      id: `demo-${i}`,
      source: "demo",
      title: `${name} #${1000 + i}`,
      collection: name,
      model: MODELS[i % MODELS.length],
      backdrop: BACKDROPS[i % BACKDROPS.length],
      symbol: null,
      number: 1000 + i,
      price_ton: price,
      currency: "TON",
      image_url: svg(name, emoji, c1, c2),
      url: "https://t.me/mrkt",
      seller: {
        id: `u-${i}`,
        username: `newbie_${i}`,
        display_name: `Новичок ${i + 1}`,
        level: 1,
        nft_count: i % 2 === 0 ? 1 : 2,
        sales_count: 0,
        is_reseller: false,
      },
      profile_url: "https://t.me/mrkt",
      novice_score: 90 - (i % 5),
      reasons: ["уровень 1", "не перекуп"],
    });
  }
  items.sort((a, b) => a.price_ton - b.price_ton);
  return items;
}

const LISTINGS = demoItems();

function send(res, code, body, type) {
  const data = Buffer.from(body);
  res.writeHead(code, {
    "Content-Type": type || "application/json; charset=utf-8",
    "Content-Length": data.length,
    "Access-Control-Allow-Origin": "*",
  });
  res.end(data);
}

function readBody(req) {
  return new Promise((resolve) => {
    const chunks = [];
    req.on("data", (c) => chunks.push(c));
    req.on("end", () => {
      const raw = Buffer.concat(chunks).toString("utf8");
      if (!raw) return resolve({});
      try {
        resolve(JSON.parse(raw));
      } catch {
        resolve({});
      }
    });
  });
}

async function tg(method, payload) {
  if (!TOKEN) return;
  await fetch(`https://api.telegram.org/bot${TOKEN}/${method}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

async function registerTelegram() {
  const base = publicBase();
  if (!TOKEN || !base.startsWith("https://")) return;
  await tg("setWebhook", { url: `${base}/webhook`, drop_pending_updates: false });
  await tg("setChatMenuButton", {
    menu_button: { type: "web_app", text: "NOVICE", web_app: { url: base } },
  });
  console.log("mini app url", base);
}

async function onUpdate(update) {
  const message = update.message;
  if (!message || !message.chat) return;
  const base = publicBase();
  const button = base.startsWith("https://")
    ? {
        inline_keyboard: [[{ text: "Открыть NOVICE", web_app: { url: base } }]],
      }
    : undefined;
  await tg("sendMessage", {
    chat_id: message.chat.id,
    text: "NOVICE ищет дешёвые Telegram NFT у новичков.\nЖми кнопку NOVICE слева от поля ввода.",
    reply_markup: button,
  });
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, "http://127.0.0.1");
  if (req.method === "OPTIONS") {
    res.writeHead(204, {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Headers": "*",
      "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
    });
    return res.end();
  }

  if (url.pathname === "/health" || url.pathname === "/api/health") {
    return send(res, 200, JSON.stringify({ ok: true, demo_mode: true }));
  }

  if (url.pathname === "/api/search") {
    const filters = {
      maxPrice: url.searchParams.get("max_price_ton") ? Number(url.searchParams.get("max_price_ton")) : null,
      minPrice: url.searchParams.get("min_price_ton") ? Number(url.searchParams.get("min_price_ton")) : null,
      query: url.searchParams.get("query") || "",
      maxLevel: Number(url.searchParams.get("max_seller_level") || 1),
      maxNfts: Number(url.searchParams.get("max_seller_nfts") || 2),
      onlyNovice: url.searchParams.get("only_novice") !== "false",
      excludeResellers: url.searchParams.get("exclude_resellers") !== "false",
      limit: 60,
    };
    const tokens = getTokens(url.searchParams.get("user_id"));
    const live = Boolean(tokens.mrkt || tokens.portals || tokens.tonnel);
    if (live) {
      try {
        return send(res, 200, JSON.stringify(await searchMarkets(tokens, filters)));
      } catch (err) {
        return send(res, 500, JSON.stringify({ detail: err.message || "Ошибка поиска" }));
      }
    }
    const query = filters.query.toLowerCase();
    let items = LISTINGS;
    if (filters.maxPrice != null) items = items.filter((item) => item.price_ton <= filters.maxPrice);
    if (query) {
      items = items.filter((item) => `${item.title} ${item.collection} ${item.model}`.toLowerCase().includes(query));
    }
    return send(
      res,
      200,
      JSON.stringify({ items, total: items.length, demo: true, sources_used: ["demo"], sources_failed: [] })
    );
  }

  if (url.pathname === "/api/accounts" && req.method === "GET") {
    return send(res, 200, JSON.stringify(accountStatus(url.searchParams.get("user_id"))));
  }

  if (url.pathname === "/api/accounts/save" && req.method === "POST") {
    const body = await readBody(req);
    saveTokens(body.user_id, body.tokens || {});
    return send(res, 200, JSON.stringify({ ok: true, ...accountStatus(body.user_id) }));
  }

  if (url.pathname === "/api/accounts/disconnect" && req.method === "POST") {
    const body = await readBody(req);
    if (body.source) saveTokens(body.user_id, { [body.source]: "" });
    return send(res, 200, JSON.stringify({ ok: true, ...accountStatus(body.user_id) }));
  }

  if (url.pathname === "/api/accounts/auto/config") {
    return send(
      res,
      200,
      JSON.stringify({
        phone_only: true,
        needs_api_setup: false,
        hint: "Номер → код из Telegram → MRKT, Portals и Tonnel привяжутся сами.",
      })
    );
  }

  if (url.pathname === "/api/accounts/auto/start" && req.method === "POST") {
    const body = await readBody(req);
    try {
      const result = await startPhoneLogin(body.phone);
      return send(res, 200, JSON.stringify(result));
    } catch (err) {
      return send(res, 400, JSON.stringify({ detail: err.message || "Не удалось отправить код" }));
    }
  }

  if (url.pathname === "/api/accounts/auto/confirm" && req.method === "POST") {
    const body = await readBody(req);
    try {
      const result = await confirmPhoneLogin(body.login_id, body.code, body.password);
      saveTokens(body.user_id, result.tokens);
      return send(
        res,
        200,
        JSON.stringify({
          ok: true,
          tokens: result.tokens,
          connected: result.connected,
          failed: result.failed,
        })
      );
    } catch (err) {
      return send(res, 400, JSON.stringify({ detail: err.message || "Не удалось войти" }));
    }
  }

  if (url.pathname === "/webhook" && req.method === "POST") {
    const update = await readBody(req);
    onUpdate(update).catch((err) => console.error(err));
    return send(res, 200, JSON.stringify({ ok: true }));
  }

  if (url.pathname === "/" || url.pathname === "/index.html") {
    return send(res, 200, fs.readFileSync(path.join(WEB, "index.html")), "text/html; charset=utf-8");
  }
  if (url.pathname === "/styles.css") {
    return send(res, 200, fs.readFileSync(path.join(WEB, "styles.css")), "text/css; charset=utf-8");
  }

  send(res, 404, JSON.stringify({ detail: "not found" }));
});

server.listen(PORT, "0.0.0.0", () => {
  console.log(`NOVICE listening on 0.0.0.0:${PORT}`);
  registerTelegram().catch((err) => console.error(err));
});
