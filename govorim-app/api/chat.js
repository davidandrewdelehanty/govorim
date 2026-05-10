// Serverless function: verifies Clerk auth, then proxies the request
// to Google Gemini in Anthropic-shaped form. Only authenticated users
// can call this endpoint, so random visitors can't burn through your
// API quota.
//
// Required env vars on Vercel:
//   GEMINI_API_KEY            — your Google AI Studio key
//   CLERK_SECRET_KEY          — your Clerk secret key (server-side)
// Optional env vars:
//   GEMINI_MODEL              — defaults to gemini-2.5-flash
//   ALLOWED_EMAILS            — comma-separated emails; if set, ONLY
//                               these users can call the API. Lock the
//                               app to yourself + a few people this way.

import { verifyToken, createClerkClient } from "@clerk/backend";

// Simple in-memory rate limiter — best-effort, resets on cold start.
const rateLimitMap = new Map();
const RATE_WINDOW_MS = 60 * 1000;
const RATE_MAX_PER_WINDOW = 15;
const RATE_DAILY_PER_IP = 200;

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
    return { ok: false, reason: "Too many requests this minute. Wait a bit." };
  }
  if (rec.dailyCount >= RATE_DAILY_PER_IP) {
    return { ok: false, reason: "Daily limit reached for your IP. Try tomorrow." };
  }
  rec.hits.push(now);
  rec.dailyCount += 1;
  rateLimitMap.set(ip, rec);
  return { ok: true };
}

// Cache the Clerk client across invocations (warm starts reuse it).
let clerkClient = null;
function getClerk() {
  if (!clerkClient) {
    clerkClient = createClerkClient({ secretKey: process.env.CLERK_SECRET_KEY });
  }
  return clerkClient;
}

export default async function handler(req, res) {
  if (req.method !== "POST") {
    return res.status(405).json({ error: "Method not allowed" });
  }

  if (!process.env.GEMINI_API_KEY) {
    return res.status(500).json({ error: "GEMINI_API_KEY not configured on the server" });
  }
  if (!process.env.CLERK_SECRET_KEY) {
    return res.status(500).json({ error: "CLERK_SECRET_KEY not configured on the server" });
  }

  // ---- Auth: require a valid Clerk JWT ----
  const authHeader = req.headers.authorization || "";
  if (!authHeader.startsWith("Bearer ")) {
    return res.status(401).json({ error: "Not signed in" });
  }
  const token = authHeader.slice(7).trim();
  let userId;
  try {
    const payload = await verifyToken(token, {
      secretKey: process.env.CLERK_SECRET_KEY,
    });
    userId = payload && payload.sub;
    if (!userId) throw new Error("No user id in token");
  } catch (err) {
    return res.status(401).json({ error: "Invalid or expired session" });
  }

  // ---- Approval gate: user must be approved by an admin to use the app ----
  // The first user (matching ADMIN_EMAIL) is auto-approved; everyone else
  // sits in pending status until the admin approves them via the admin UI.
  try {
    const user = await getClerk().users.getUser(userId);
    const email = user && user.primaryEmailAddress
      ? (user.primaryEmailAddress.emailAddress || "").toLowerCase()
      : "";
    const adminEmail = (process.env.ADMIN_EMAIL || "").toLowerCase();
    const meta = (user && user.publicMetadata) || {};
    const isAdmin = !!adminEmail && email === adminEmail;
    const isApproved = meta.approved === true || isAdmin;

    if (!isApproved) {
      return res.status(403).json({
        error: "PENDING_APPROVAL",
        message: "Your account is pending approval. You'll receive an email once you're approved."
      });
    }
  } catch (err) {
    return res.status(500).json({ error: "Could not verify user: " + (err.message || err) });
  }

  // ---- Per-IP rate limit (cheap layer of abuse protection) ----
  const ip = getClientIp(req);
  const rl = checkRateLimit(ip);
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

  // ---- Translate Anthropic-shaped messages → Gemini format ----
  const contents = messages.map(function(m) {
    return {
      role: m.role === "assistant" ? "model" : "user",
      parts: [{ text: typeof m.content === "string" ? m.content : "" }],
    };
  });

  const model = process.env.GEMINI_MODEL || "gemini-2.5-flash";
  const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${process.env.GEMINI_API_KEY}`;
  const payload = {
    contents: contents,
    generationConfig: { maxOutputTokens: max_tokens, temperature: 1.0 },
  };
  if (system && system.trim()) {
    payload.systemInstruction = { parts: [{ text: system }] };
  }

  // ---- Call Gemini ----
  try {
    const ctrl = new AbortController();
    const tid = setTimeout(function(){ ctrl.abort(); }, 25000);

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
      const msg = (data && data.error && data.error.message) || text.slice(0, 300) || ("HTTP " + r.status);
      return res.status(r.status).json({ error: "Gemini: " + msg });
    }

    const out = data && data.candidates && data.candidates[0] && data.candidates[0].content
      && data.candidates[0].content.parts && data.candidates[0].content.parts[0]
      ? data.candidates[0].content.parts[0].text || ""
      : "";

    return res.status(200).json({ text: out });
  } catch (err) {
    const isAbort = err && err.name === "AbortError";
    return res.status(isAbort ? 504 : 500).json({
      error: isAbort ? "Gemini timed out" : ("Server error: " + (err.message || err)),
    });
  }
}
