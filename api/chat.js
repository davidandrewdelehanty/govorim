// Serverless function: translates the frontend's Anthropic-shaped request
// into a Gemini API call, returns a normalized { text } response.
//
// Required environment variable on Vercel: GEMINI_API_KEY
// Optional: GEMINI_MODEL (defaults to gemini-2.5-flash)

// Simple in-memory rate limiter — best-effort, resets on cold start.
// For a low-traffic personal app this is enough; if you need durable
// rate limiting later, swap this for Upstash Redis or Vercel KV.
const rateLimitMap = new Map();
const RATE_WINDOW_MS = 60 * 1000;        // 1-minute window
const RATE_MAX_PER_WINDOW = 15;          // 15 requests per IP per minute
const RATE_DAILY_PER_IP = 200;           // 200 requests per IP per day

function getClientIp(req) {
  const fwd = req.headers["x-forwarded-for"];
  if (typeof fwd === "string" && fwd.length) return fwd.split(",")[0].trim();
  return req.headers["x-real-ip"] || "unknown";
}

function checkRateLimit(ip) {
  const now = Date.now();
  const day = Math.floor(now / (24 * 60 * 60 * 1000));
  const rec = rateLimitMap.get(ip) || { hits: [], dailyKey: day, dailyCount: 0 };

  // Reset daily counter when day rolls over
  if (rec.dailyKey !== day) { rec.dailyKey = day; rec.dailyCount = 0; }

  // Drop hits outside the rolling minute window
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

export default async function handler(req, res) {
  if (req.method !== "POST") {
    return res.status(405).json({ error: "Method not allowed" });
  }

  if (!process.env.GEMINI_API_KEY) {
    return res.status(500).json({ error: "GEMINI_API_KEY not configured on the server" });
  }

  // Rate limit per client IP
  const ip = getClientIp(req);
  const rl = checkRateLimit(ip);
  if (!rl.ok) return res.status(429).json({ error: rl.reason });

  let body = req.body;
  if (typeof body === "string") {
    try { body = JSON.parse(body); } catch { body = {}; }
  }
  const { messages = [], system = "", max_tokens = 400 } = body || {};

  if (!Array.isArray(messages) || messages.length === 0) {
    return res.status(400).json({ error: "Missing messages" });
  }

  // Anthropic message format: { role: "user"|"assistant", content: "string" }
  // Gemini expects: { role: "user"|"model", parts: [{ text: "string" }] }
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
    generationConfig: {
      maxOutputTokens: max_tokens,
      temperature: 1.0,
    },
  };
  if (system && system.trim()) {
    payload.systemInstruction = { parts: [{ text: system }] };
  }

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
