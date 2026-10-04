"use strict";

const fs = require("fs");
const path = require("path");

const DATA = process.env.DATA_DIR || "/app/data";

function userPath(userId) {
  const safe = String(userId || "local").replace(/[^a-zA-Z0-9_-]/g, "").slice(0, 64) || "local";
  return path.join(DATA, "users", `${safe}.json`);
}

function readUser(userId) {
  const file = userPath(userId);
  try {
    return JSON.parse(fs.readFileSync(file, "utf8"));
  } catch {
    return { tokens: {} };
  }
}

function writeUser(userId, data) {
  const file = userPath(userId);
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, JSON.stringify(data, null, 2));
  return data;
}

function getTokens(userId) {
  const tokens = readUser(userId).tokens || {};
  return {
    mrkt: tokens.mrkt || "",
    portals: tokens.portals || "",
    tonnel: tokens.tonnel || "",
  };
}

function saveTokens(userId, partial) {
  const current = readUser(userId);
  const tokens = { ...(current.tokens || {}) };
  for (const key of ["mrkt", "portals", "tonnel"]) {
    if (partial[key] === undefined) continue;
    if (!partial[key]) delete tokens[key];
    else tokens[key] = String(partial[key]);
  }
  writeUser(userId, { ...current, tokens });
  return tokens;
}

function accountStatus(userId) {
  const tokens = getTokens(userId);
  const accounts = ["mrkt", "portals", "tonnel"].map((source) => ({
    source,
    connected: Boolean(tokens[source]),
  }));
  return {
    accounts,
    connected_count: accounts.filter((row) => row.connected).length,
  };
}

module.exports = { getTokens, saveTokens, accountStatus };
