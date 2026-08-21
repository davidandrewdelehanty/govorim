// Serverless function: proxies a request to an AI provider (Google Gemini or
// Anthropic Claude). The site is public, so this endpoint is public too --
// definitions and comprehension questions work signed out. What protects it
// is the per-IP rate limit below, not a login.
//
// FREE BY DEFAULT:
// Only the free provider (Gemini) is used. The paid Anthropic path still exists
// but is OFF unless ALLOW_PAID_FALLBACK is set to a truthy value — otherwise a
// quota-exhausted Gemini would silently start spending money, which is exactly
// what we do not want for something as high-volume as word definitions. With
// the fallback off, an exhausted quota surfaces to the user as a clear message.
//
// Required env vars on Vercel:
//   GEMINI_API_KEY            — Google AI Studio key (required for Gemini path)
//   ANTHROPIC_API_KEY         — Anthropic API key (required for Claude path)
//   At minimum one of GEMINI_API_KEY / ANTHROPIC_API_KEY must be set.
// Optional env vars:
//   PROVIDER                  — "gemini" (default) or "anthropic".
//   ALLOW_PAID_FALLBACK       — unset/false (default): free provider only. Set
//                               to 1/true to re-enable falling back to the paid
//                               provider when the free quota is exhausted.
//   GEMINI_THINKING           — unset (default): thinking disabled on Gemini 2.5
//                               models. Set to a token budget to re-enable.
//   GEMINI_MODEL              — defaults to gemini-3.6-flash. Google retires
//                               older aliases; if definitions start failing with
//                               a 404 about "models/...", this is what to change.
//   ANTHROPIC_MODEL           — defaults to claude-haiku-4-5-20251001

import { currentUser } from "../lib/auth.js";

// Simple in-memory rate limiter — best-effort, resets on cold start.
const rateLimitMap = new Map();
const RATE_WINDOW_MS = 60 * 1000;
// Signed-out visitors get a smaller allowance than account holders. The app
// asks for a definition on every word tap, so the per-minute number has to
// stay usable for real reading while still capping what one IP can burn of
// the shared free Gemini quota.
const RATE_MAX_PER_WINDOW = 15;
const RATE_DAILY_PER_IP = 200;
const RATE_MAX_PER_WINDOW_ANON = 10;
const RATE_DAILY_PER_IP_ANON = 100;

function getClientIp(req) {
  const fwd = req.headers["x-forwarded-for"];
  if (typeof fwd === "string" && fwd.length) return fwd.split(",")[0].trim();
  return req.headers["x-real-ip"] || "unknown";
}

function checkRateLimit(ip, signedIn) {
  const perWindow = signedIn ? RATE_MAX_PER_WINDOW : RATE_MAX_PER_WINDOW_ANON;
  const perDay = signedIn ? RATE_DAILY_PER_IP : RATE_DAILY_PER_IP_ANON;
  const now = Date.now();
  const day = Math.floor(now / (24 * 60 * 60 * 1000));
  const rec = rateLimitMap.get(ip) || { hits: [], dailyKey: day, dailyCount: 0 };
  if (rec.dailyKey !== day) { rec.dailyKey = day; rec.dailyCount = 0; }
  rec.hits = rec.hits.filter(function(t){ return now - t < RATE_WINDOW_MS; });
  if (rec.hits.length >= perWindow) {
    return { ok: false, reason: "Too many requests this minute. Wait a bit." };
  }
  if (rec.dailyCount >= perDay) {
    return { ok: false, reason: "Daily limit reached for your IP. Try tomorrow." };
  }
  rec.hits.push(now);
  rec.dailyCount += 1;
  rateLimitMap.set(ip, rec);
  return { ok: true };
}

export default async function handler(req, res) {
  if (req.method !== "POST") {
    return res.status(405).json({ error: "Method not allowed" });
  }

  if (!process.env.GEMINI_API_KEY) {
    return res.status(500).json({ error: "GEMINI_API_KEY not configured on the server" });
  }
  // ---- Per-IP rate limit (cheap layer of abuse protection) ----
  const ip = getClientIp(req);
  // Resolve the signed-in user once: the rate limiter needs to know whether
  // there is one, and callProvider() logs the id. Calling currentUser() only
  // inline in the rate-limit check left `userId` undeclared further down, and
  // because ES modules are strict mode that threw a ReferenceError on EVERY
  // request rather than logging a blank user.
  const user = currentUser(req);
  const userId = user ? user.id : null;
  const rl = checkRateLimit(ip, !!user);
  if (!rl.ok) return res.status(429).json({ error: rl.reason });

  // ---- Parse body ----
  let body = req.body;
  if (typeof body === "string") {
    try { body = JSON.parse(body); } catch { body = {}; }
  }
  const { messages = [], system = "", max_tokens = 2048 } = body || {};

  if (!Array.isArray(messages) || messages.length === 0) {
    return res.status(400).json({ error: "Missing messages" });
  }

  // ---- Per-request type tag (visible in Vercel Logs) ────────────────────────
  // Cheap heuristic to label what each call was for, so logs are readable when
  // diagnosing quota burn. Doesn't affect behavior — just helps us see
  // "definition calls are 80% of usage" at a glance.
  const sys0 = (system || "").toLowerCase();
  const firstMsg = (messages[0] && messages[0].content) || "";
  let callType = "chat";
  if (body && body.json && /dictionary/i.test(system))           callType = "definition";
  else if (sys0.indexOf("comprehension tutor") !== -1)            callType = "comprehension";
  else if (typeof firstMsg === "string" && firstMsg === "Go.")    callType = "comprehension";
  else if (typeof firstMsg === "string" && firstMsg === "Start please.") callType = "chat-start";
  // ───────────────────────────────────────────────────────────────────────────

  const wantJson = !!(body && body.json);
  // PROVIDER env var picks the primary upstream AI. Default is "gemini".
  // If the OTHER provider's API key is configured, the backend will
  // automatically fall back to it when the primary returns a quota/rate-limit
  // error (HTTP 429 or quota-flavored 403). This gives you "free Gemini until
  // it runs out, then Claude" automatically — no env-var-flipping needed.
  const primary = (process.env.PROVIDER || "gemini").toLowerCase();
  const chain = providerChain(primary);
  if (chain.length === 0) {
    return res.status(500).json({ error: "No AI provider configured. Set GEMINI_API_KEY and/or ANTHROPIC_API_KEY." });
  }

  // Skip providers we've recently seen exhaust their quota — but if EVERY
  // provider in the chain is currently marked exhausted, try them anyway
  // (better one bad call than failing the user completely).
  let tryOrder = chain.filter(function(p){ return !isExhausted(p); });
  if (tryOrder.length === 0) tryOrder = chain;

  let lastErr = null;
  for (let i = 0; i < tryOrder.length; i++) {
    const providerName = tryOrder[i];
    try {
      const out = await callProvider(providerName, { messages, system, max_tokens, wantJson, callType, ip, userId });
      // Successful call — if we previously marked this provider exhausted, clear it.
      exhaustedUntil.delete(providerName);
      return res.status(200).json({ text: out });
    } catch (err) {
      lastErr = err;
      if (isQuotaError(err)) {
        // Mark this provider exhausted for an appropriate window — short if it
        // looks like a per-minute rate cap, long if it looks like the daily cap.
        const backoff = quotaBackoffMs(err);
        markExhausted(providerName, backoff);
        const next = tryOrder[i + 1];
        console.log("[ai] " + providerName + " quota hit (" + Math.round(backoff/1000/60) + "min backoff)" + (next ? " — falling back to " + next : " — no fallback available"));
        continue; // try next provider in chain
      }
      // Non-quota error (auth, server, network): don't waste a fallback call.
      break;
    }
  }

  // All providers failed — return the last error.
  const isAbort = lastErr && lastErr.name === "AbortError";
  const status = lastErr && lastErr.status ? lastErr.status : (isAbort ? 504 : 500);
  return res.status(status).json({
    error: isAbort ? "AI request timed out" : (lastErr && lastErr.message ? lastErr.message : "Server error"),
  });
}

// ── Provider chain & exhaustion tracking ─────────────────────────────────────
// In-memory state, best-effort. Resets on Vercel cold start (every ~5min idle).
const exhaustedUntil = new Map(); // providerName → ms timestamp when it should be retried
const DEFAULT_BACKOFF_MS = 2 * 60 * 1000;       // 2 minutes (per-minute caps / unknown)
const DAILY_BACKOFF_MS   = 60 * 60 * 1000;      // 1 hour (per-day caps; we'll re-test hourly)

function isExhausted(name) {
  const until = exhaustedUntil.get(name);
  return !!(until && Date.now() < until);
}
function markExhausted(name, ms) {
  exhaustedUntil.set(name, Date.now() + (ms || DEFAULT_BACKOFF_MS));
}
function isQuotaError(err) {
  if (!err) return false;
  if (err.status === 429) return true;
  // Some 403s are quota-flavored (Gemini's RESOURCE_EXHAUSTED, Anthropic billing).
  if (err.status === 403 && /quota|exceeded|exhaust|rate|insufficient|credit/i.test(err.message || "")) return true;
  return false;
}
function quotaBackoffMs(err) {
  const msg = (err && err.message) || "";
  // Heuristic: Gemini per-day quotas have "PerDay" in the violation message.
  if (/per.?day/i.test(msg)) return DAILY_BACKOFF_MS;
  // Anthropic spend limits / billing issues are also "until tomorrow"-ish.
  if (/spend|credit|insufficient/i.test(msg)) return DAILY_BACKOFF_MS;
  return DEFAULT_BACKOFF_MS;
}
// Build the provider chain: primary first, then the other one as fallback if its
// key is configured. Skips providers whose keys aren't set so we don't trip on
// "missing API key" errors mid-fallback.
function providerChain(primary) {
  const hasGemini    = !!process.env.GEMINI_API_KEY;
  const hasAnthropic = !!process.env.ANTHROPIC_API_KEY;
  // The paid provider is opt-in. Without this guard, exhausting the free daily
  // quota quietly moves every definition lookup onto a billed API.
  const allowPaid = /^(1|true|yes|on)$/i.test(process.env.ALLOW_PAID_FALLBACK || "");
  const order = [];
  if (primary === "anthropic" || primary === "claude") {
    if (hasAnthropic) order.push("anthropic");
    if (hasGemini)    order.push("gemini");
  } else {
    if (hasGemini)    order.push("gemini");
    if (hasAnthropic && allowPaid) order.push("anthropic");
  }
  return order;
}
async function callProvider(name, params) {
  if (name === "anthropic" || name === "claude") return callAnthropic(params);
  return callGemini(params);
}

// ── Gemini call ──────────────────────────────────────────────────────────────
async function callGemini({ messages, system, max_tokens, wantJson, callType, ip, userId }) {
  if (!process.env.GEMINI_API_KEY) {
    const e = new Error("GEMINI_API_KEY not configured on the server");
    e.status = 500; throw e;
  }
  // Anthropic-shaped messages → Gemini contents
  const contents = messages.map(function(m) {
    return {
      role: m.role === "assistant" ? "model" : "user",
      parts: [{ text: typeof m.content === "string" ? m.content : "" }],
    };
  });

  // Google retires model aliases, and the failure is a 404 that reads like a
  // bug in our code rather than an expired name. GEMINI_MODEL overrides this,
  // so when a model is retired the env var has to be updated or removed too —
  // a stale env var will keep pinning a dead model no matter what this says.
  const model = process.env.GEMINI_MODEL || "gemini-3.6-flash";
  console.log("[ai] provider=gemini call type=" + callType + " ip=" + ip + " user=" + (userId || "?") + " model=" + model + " msgs=" + messages.length);

  const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${process.env.GEMINI_API_KEY}`;
  // JSON mode: strict structured output + lower temperature. Otherwise default
  // creative settings.
  const generationConfig = wantJson
    ? { maxOutputTokens: max_tokens, temperature: 0.2, responseMimeType: "application/json" }
    : { maxOutputTokens: max_tokens, temperature: 1.0 };
  // Gemini models from 2.5 on think before answering, and those thinking tokens
  // are billed against maxOutputTokens. A small JSON reply can therefore come
  // back completely EMPTY with finishReason MAX_TOKENS — the model spent the
  // whole budget reasoning and had nothing left to emit. Word definitions do not
  // need deliberation, so thinking is held as low as each family allows.
  //
  // The two families are configured DIFFERENTLY, and mixing them up is a 400:
  //   2.5–2.9  thinkingConfig.thinkingBudget — a token count, 0 disables.
  //   3.x+     thinkingConfig.thinkingLevel  — "minimal" | "low" | "high".
  //            Flash and Flash-Lite cannot turn thinking off at all, so
  //            thinkingBudget: 0 here is rejected outright with
  //            INVALID_ARGUMENT ("request contains an invalid argument").
  //            "minimal" is the floor; it does not guarantee zero thinking.
  if (/^gemini-([3-9]|\d{2,})/.test(model)) {
    const level = (process.env.GEMINI_THINKING_LEVEL || "minimal").toLowerCase();
    generationConfig.thinkingConfig = { thinkingLevel: level };
  } else if (/^gemini-2\.[5-9]/.test(model) || /-thinking/.test(model)) {
    const budget = parseInt(process.env.GEMINI_THINKING || "0", 10);
    generationConfig.thinkingConfig = { thinkingBudget: isNaN(budget) ? 0 : budget };
  }
  const payload = { contents, generationConfig };
  if (system && system.trim()) {
    payload.systemInstruction = { parts: [{ text: system }] };
  }

  const ctrl = new AbortController();
  const tid = setTimeout(() => ctrl.abort(), 25000);
  const r = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal: ctrl.signal,
  });
  clearTimeout(tid);

  const text = await r.text();
  let data;
  try { data = JSON.parse(text); } catch { data = null; }
  if (!r.ok) {
    let msg = (data && data.error && data.error.message) || text.slice(0, 300) || ("HTTP " + r.status);
    // A retired or misspelled model comes back as a 404 whose text is about
    // "models/<name>". Name the env var, because that is what has to change.
    if (r.status === 404 && /model/i.test(msg)) {
      msg += " — the model name is set by GEMINI_MODEL (currently \"" + model +
             "\"); update or delete that env var.";
    }
    // INVALID_ARGUMENT's top-level message is generic ("request contains an
    // invalid argument") and never names the offending field; the detail that
    // does is buried in error.details. Without this the only way to find out
    // which key Google rejected is to bisect the payload by hand.
    if (r.status === 400) {
      const details = (data && data.error && data.error.details) || [];
      const notes = details
        .map(function(d){ return d && (d.fieldViolations || d.field_violations); })
        .filter(Boolean)
        .reduce(function(a, b){ return a.concat(b); }, [])
        .map(function(v){ return (v.field || "?") + ": " + (v.description || ""); });
      if (notes.length) msg += " — " + notes.join("; ");
      msg += " [model=" + model + ", generationConfig keys: " +
             Object.keys(generationConfig).join(",") + "]";
    }
    const e = new Error("Gemini: " + msg); e.status = r.status; throw e;
  }
  // Read EVERY part, not just the first — a reply split across parts would
  // otherwise be silently truncated.
  const cand = data && data.candidates && data.candidates[0];
  const parts = (cand && cand.content && cand.content.parts) || [];
  const out = parts.map(function(p){ return (p && p.text) || ""; }).join("");
  if (out.trim()) return out;

  // Empty reply. Returning "" here is what used to surface downstream as the
  // baffling "returned no JSON object / (empty)" — say what actually happened.
  const finish = (cand && cand.finishReason) || "";
  const blocked = data && data.promptFeedback && data.promptFeedback.blockReason;
  const usage = (data && data.usageMetadata) || {};
  console.log("[ai] gemini empty reply finishReason=" + finish + " block=" + (blocked || "-") +
              " thoughts=" + (usage.thoughtsTokenCount || 0) +
              " out=" + (usage.candidatesTokenCount || 0));
  let why;
  if (blocked)                   why = "the prompt was blocked (" + blocked + ")";
  else if (finish === "MAX_TOKENS") why = "it hit the output limit before writing anything — raise max_tokens or lower GEMINI_THINKING";
  else if (finish === "SAFETY")  why = "the response was filtered for safety";
  else if (finish)               why = "it stopped early (" + finish + ")";
  else                           why = "no candidates were returned";
  const e = new Error("Gemini returned an empty response: " + why);
  e.status = 502;
  throw e;
}

// ── Anthropic / Claude call ──────────────────────────────────────────────────
// Uses raw fetch (no SDK) for consistency with the Gemini path and to avoid
// shipping another dependency. The frontend doesn't know or care which provider
// served the response — it just gets {text: "..."} either way.
async function callAnthropic({ messages, system, max_tokens, wantJson, callType, ip, userId }) {
  if (!process.env.ANTHROPIC_API_KEY) {
    const e = new Error("ANTHROPIC_API_KEY not configured on the server");
    e.status = 500; throw e;
  }
  // Default to Haiku 4.5 — fast + cheap, plenty good for dictionary/comprehension
  // work. Override via ANTHROPIC_MODEL env var (e.g. claude-sonnet-4-6 for higher
  // quality at higher cost).
  const model = process.env.ANTHROPIC_MODEL || "claude-haiku-4-5-20251001";
  console.log("[ai] provider=anthropic call type=" + callType + " ip=" + ip + " user=" + (userId || "?") + " model=" + model + " msgs=" + messages.length);

  // Anthropic message shape: role + string content. Drop any non-string content.
  const aMessages = messages.map(function(m) {
    return {
      role: m.role === "model" ? "assistant" : (m.role || "user"),
      content: typeof m.content === "string" ? m.content : "",
    };
  }).filter(function(m){ return m.content.length > 0; });

  // JSON mode for Claude: no built-in `responseMimeType` like Gemini, but the
  // model follows clear instructions reliably. Lower temperature on top, and
  // reinforce the system prompt with a "JSON only" note if one isn't already
  // baked in.
  const sysOut = wantJson
    ? (system ? system + "\n\nReturn a single JSON object. No markdown, no prose, no commentary." : "Return a single JSON object. No markdown, no prose, no commentary.")
    : system;

  const payload = {
    model,
    max_tokens,
    temperature: wantJson ? 0.2 : 1.0,
    messages: aMessages,
  };
  if (sysOut && sysOut.trim()) payload.system = sysOut;

  const ctrl = new AbortController();
  const tid = setTimeout(() => ctrl.abort(), 25000);
  const r = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: {
      "x-api-key": process.env.ANTHROPIC_API_KEY,
      "anthropic-version": "2023-06-01",
      "content-type": "application/json",
    },
    body: JSON.stringify(payload),
    signal: ctrl.signal,
  });
  clearTimeout(tid);

  const text = await r.text();
  let data;
  try { data = JSON.parse(text); } catch { data = null; }
  if (!r.ok) {
    const msg = (data && data.error && data.error.message) || text.slice(0, 300) || ("HTTP " + r.status);
    const e = new Error("Anthropic: " + msg); e.status = r.status; throw e;
  }
  // Concatenate all text content blocks (Anthropic returns content[] with mixed types).
  const blocks = (data && Array.isArray(data.content)) ? data.content : [];
  return blocks
    .filter(function(b){ return b && b.type === "text" && typeof b.text === "string"; })
    .map(function(b){ return b.text; })
    .join("");
}
