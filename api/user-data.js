// /api/user-data.js
// Stores per-user vocab and grammar tips in Clerk privateMetadata.
// GET fetches the user's saved data. POST replaces it.
// Clerk metadata has an 8KB limit per user — enough for ~200 vocab entries
// depending on how detailed each entry is. If we hit the limit, we'd switch
// to Upstash Redis (free tier) but for now Clerk metadata is simpler.

import { verifyToken, createClerkClient } from "@clerk/backend";

const clerk = createClerkClient({ secretKey: process.env.CLERK_SECRET_KEY });

export default async function handler(req, res) {
  // Extract bearer token from Authorization header
  const authHeader = req.headers.authorization || "";
  const token = authHeader.startsWith("Bearer ") ? authHeader.slice(7) : "";
  if (!token) return res.status(401).json({ error: "Missing auth token" });

  let userId;
  try {
    const payload = await verifyToken(token, { secretKey: process.env.CLERK_SECRET_KEY });
    userId = payload.sub;
  } catch (e) {
    return res.status(401).json({ error: "Invalid auth token" });
  }
  if (!userId) return res.status(401).json({ error: "No user in token" });

  try {
    if (req.method === "GET") {
      const user = await clerk.users.getUser(userId);
      const meta = user.privateMetadata || {};
      return res.status(200).json({
        vocab: Array.isArray(meta.vocab) ? meta.vocab : [],
        tips:  Array.isArray(meta.tips)  ? meta.tips  : [],
      });
    }

    if (req.method === "POST") {
      const body = typeof req.body === "string" ? JSON.parse(req.body) : (req.body || {});
      const vocab = Array.isArray(body.vocab) ? body.vocab : [];
      const tips  = Array.isArray(body.tips)  ? body.tips  : [];

      // Trim entries down to essential fields so we don't blow past Clerk's 8KB limit.
      const slimVocab = vocab.map(function(v) {
        if (typeof v === "string") return { ru: v };
        if (!v || typeof v !== "object") return null;
        const out = {};
        if (v.ru) out.ru = v.ru;
        if (v.en) out.en = v.en;
        if (v.pos) out.pos = v.pos;
        if (v.grammar) out.grammar = v.grammar;
        if (v.example) out.example = v.example;
        if (v.created) out.created = v.created;
        if (v.id && !v.created) out.id = v.id;  // legacy fallback
        return out;
      }).filter(Boolean);

      const slimTips = tips.map(function(t) {
        return typeof t === "string" ? t : (t && t.text) ? t.text : "";
      }).filter(Boolean);

      await clerk.users.updateUser(userId, {
        privateMetadata: { vocab: slimVocab, tips: slimTips },
      });
      return res.status(200).json({ ok: true, count: { vocab: slimVocab.length, tips: slimTips.length } });
    }

    return res.status(405).json({ error: "Method not allowed" });
  } catch (e) {
    // Clerk's metadata size cap surfaces as a 422 with a clear message — pass it through.
    const msg = e && e.message ? e.message : "Server error";
    const status = msg.toLowerCase().includes("size") || msg.toLowerCase().includes("limit") ? 413 : 500;
    return res.status(status).json({ error: msg });
  }
}
