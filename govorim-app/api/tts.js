// Serverless function: proxies text-to-speech requests to Azure Speech Services.
// The Azure subscription key NEVER reaches the client — it stays server-side via
// the AZURE_SPEECH_KEY env var. Returns audio bytes (MP3) on success.
//
// Required env vars on Vercel:
//   CLERK_SECRET_KEY      — Clerk secret (server-side auth check)
//   AZURE_SPEECH_KEY      — Azure subscription key
//   AZURE_SPEECH_REGION   — Azure region (e.g. "eastus", "westeurope")
// Optional:
//   ALLOWED_EMAILS        — same allowlist used by chat.js
//
// Response shape:
//   200 OK with Content-Type: audio/mpeg, body = audio bytes
//   429 if rate-limited (per-IP or Azure quota exhausted)
//   4xx/5xx with JSON { error: "..." } for everything else
//
// The frontend uses 429 (and 5xx with a quota-flavored message) as the signal to
// fall back to a browser-native voice (Google русский).

import { verifyToken, createClerkClient } from "@clerk/backend";

// Per-IP rate limiter — separate from chat.js because TTS calls are larger
// (~1700 chars typical) and cost real money against the Azure quota. We cap
// generously since one reader naturally fires ~1 call per page flip.
const rateLimitMap = new Map();
const RATE_WINDOW_MS = 60 * 1000;
const RATE_MAX_PER_WINDOW = 30;          // 30 TTS calls per minute per IP
const RATE_DAILY_PER_IP = 500;            // 500 daily — heavy reading still fine

function getClientIp(req) {
  const fwd = req.headers["x-forwarded-for"];
  if (typeof fwd === "string" && fwd.length) return fwd.split(",")[0].trim();
  return req.headers["x-real-ip"] || "unknown";
}

function checkRateLimit(ip) {
  const now = Date.now();
  const day = Math.floor(now / (24 * 60 * 60 * 1000));
  const rec = rateLimitMap.get(ip) || { hits: [], dailyKey: day, dailyCount: 0 };
  if (rec.dailyKey !== day) { rec.dailyKey = day; rec.dailyCount = 0; }
  rec.hits = rec.hits.filter(function(t){ return now - t < RATE_WINDOW_MS; });
  if (rec.hits.length >= RATE_MAX_PER_WINDOW) {
    return { ok: false, reason: "Too many TTS requests this minute. Wait a bit." };
  }
  if (rec.dailyCount >= RATE_DAILY_PER_IP) {
    return { ok: false, reason: "Daily TTS limit reached for your IP." };
  }
  rec.hits.push(now);
  rec.dailyCount += 1;
  rateLimitMap.set(ip, rec);
  return { ok: true };
}

let clerkClient = null;
function getClerk() {
  if (!clerkClient) clerkClient = createClerkClient({ secretKey: process.env.CLERK_SECRET_KEY });
  return clerkClient;
}

// XML escape so user-supplied book text can't break SSML or inject markup.
function escapeXml(s) {
  return String(s || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

export default async function handler(req, res) {
  if (req.method !== "POST") {
    return res.status(405).json({ error: "Method not allowed" });
  }

  // ---- Auth: verify Clerk JWT ────────────────────────────────────────────────
  const authHeader = req.headers.authorization || "";
  const token = authHeader.startsWith("Bearer ") ? authHeader.slice(7) : "";
  if (!token) return res.status(401).json({ error: "Missing auth token" });

  let userId, sessionClaims;
  try {
    const verified = await verifyToken(token, { secretKey: process.env.CLERK_SECRET_KEY });
    userId = verified.sub;
    sessionClaims = verified;
  } catch (e) {
    return res.status(401).json({ error: "Invalid auth token" });
  }

  // ---- Optional approval check (same as chat.js) ─────────────────────────────
  if (process.env.ALLOWED_EMAILS) {
    try {
      const user = await getClerk().users.getUser(userId);
      const email = (user.emailAddresses && user.emailAddresses[0] && user.emailAddresses[0].emailAddress) || "";
      const allowed = process.env.ALLOWED_EMAILS.split(",").map(function(s){ return s.trim().toLowerCase(); });
      if (!allowed.includes(email.toLowerCase())) {
        return res.status(403).json({ error: "PENDING_APPROVAL" });
      }
    } catch (e) { /* fall through */ }
  }

  // ---- Rate limit per IP ─────────────────────────────────────────────────────
  const ip = getClientIp(req);
  const rl = checkRateLimit(ip);
  if (!rl.ok) return res.status(429).json({ error: rl.reason });

  // ---- Body validation ───────────────────────────────────────────────────────
  // Parse the body either when Vercel hands us a parsed object or a raw string.
  let body = req.body;
  if (typeof body === "string") {
    try { body = JSON.parse(body); } catch { body = {}; }
  }
  const text = body && typeof body.text === "string" ? body.text : "";
  const voice = body && typeof body.voice === "string" ? body.voice : "";
  if (!text.trim()) return res.status(400).json({ error: "Missing text" });
  if (!voice) return res.status(400).json({ error: "Missing voice" });

  // ---- Config check ─────────────────────────────────────────────────────────
  if (!process.env.AZURE_SPEECH_KEY || !process.env.AZURE_SPEECH_REGION) {
    return res.status(500).json({ error: "Azure Speech not configured on the server" });
  }

  // Cap text at 5000 chars/request — Azure's hard limit is ~10k for a single
  // request, and we want responses to come back within Vercel's 25s function
  // budget. The frontend chunks longer text into multiple sequential calls.
  const limitedText = text.slice(0, 5000);

  // Build SSML. Voice name (e.g. "ru-RU-DmitryNeural") goes in the voice tag.
  // Wrapping in <prosody rate="-10%"> slows it down a touch for learners.
  const ssml =
    '<speak version="1.0" xml:lang="ru-RU" xmlns="http://www.w3.org/2001/10/synthesis">' +
      '<voice name="' + escapeXml(voice) + '">' +
        '<prosody rate="-10%">' + escapeXml(limitedText) + '</prosody>' +
      '</voice>' +
    '</speak>';

  const region = process.env.AZURE_SPEECH_REGION;
  const url = "https://" + region + ".tts.speech.microsoft.com/cognitiveservices/v1";

  console.log("[azure-tts] voice=" + voice + " chars=" + limitedText.length + " ip=" + ip + " user=" + (userId || "?"));

  try {
    const ctrl = new AbortController();
    const tid = setTimeout(function(){ ctrl.abort(); }, 25000);

    const r = await fetch(url, {
      method: "POST",
      headers: {
        "Ocp-Apim-Subscription-Key": process.env.AZURE_SPEECH_KEY,
        "Content-Type":             "application/ssml+xml",
        "X-Microsoft-OutputFormat": "audio-24khz-48kbitrate-mono-mp3",
        "User-Agent":               "govorim/1.0",
      },
      body: ssml,
      signal: ctrl.signal,
    });
    clearTimeout(tid);

    if (!r.ok) {
      // Pull the error body so the frontend can decide whether to fall back.
      let errText = "";
      try { errText = await r.text(); } catch {}
      // Azure returns 429 for both per-second rate limits AND monthly quota
      // exhaustion. Either way the client should fall back to a free voice.
      return res.status(r.status).json({
        error: "Azure: HTTP " + r.status + (errText ? " — " + errText.slice(0, 200) : ""),
      });
    }

    const buf = await r.arrayBuffer();
    res.setHeader("Content-Type", "audio/mpeg");
    res.setHeader("Cache-Control", "no-store");
    return res.status(200).send(Buffer.from(buf));
  } catch (err) {
    const isAbort = err && err.name === "AbortError";
    return res.status(isAbort ? 504 : 500).json({
      error: isAbort ? "Azure TTS timed out" : ("Server error: " + (err.message || err)),
    });
  }
}
