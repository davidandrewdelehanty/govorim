// /api/user-data.js
// Stores per-user data in Cloudflare R2 (S3-compatible), keyed by Clerk userId.
// Auth: Clerk bearer token (unchanged from previous version).
// Storage: r2:govorim-audio/userdata/{userId}/{type}.json
// Separate files per data type: vocab, tips, progress, settings.
// No size limit (R2 has none). Migration: on first GET, seeds from Clerk metadata.
import { verifyToken, createClerkClient } from "@clerk/backend";
import {
  S3Client, GetObjectCommand, PutObjectCommand
} from "@aws-sdk/client-s3";

const clerk = createClerkClient({ secretKey: process.env.CLERK_SECRET_KEY });

const s3 = new S3Client({
  region: "auto",
  endpoint: process.env.R2_ENDPOINT,
  credentials: {
    accessKeyId:     process.env.R2_ACCESS_KEY_ID,
    secretAccessKey: process.env.R2_SECRET_ACCESS_KEY,
  },
});

const BUCKET = "govorim-audio";
const PREFIX = "userdata";

// ── R2 helpers ────────────────────────────────────────────────────────────────
async function r2Get(userId, type) {
  try {
    const cmd = new GetObjectCommand({
      Bucket: BUCKET,
      Key: `${PREFIX}/${userId}/${type}.json`,
    });
    const resp = await s3.send(cmd);
    const text = await resp.Body.transformToString();
    return JSON.parse(text);
  } catch (e) {
    if (e.name === "NoSuchKey" || e.$metadata?.httpStatusCode === 404) return null;
    throw e;
  }
}

async function r2Put(userId, type, data) {
  const cmd = new PutObjectCommand({
    Bucket: BUCKET,
    Key: `${PREFIX}/${userId}/${type}.json`,
    Body: JSON.stringify(data, null, 2),
    ContentType: "application/json",
  });
  await s3.send(cmd);
}

// ── Migration: seed R2 from Clerk metadata on first use ───────────────────────
async function migrateFromClerk(userId) {
  try {
    const user = await clerk.users.getUser(userId);
    const meta = user.privateMetadata || {};
    const vocab = Array.isArray(meta.vocab) ? meta.vocab : [];
    const tips  = Array.isArray(meta.tips)  ? meta.tips  : [];
    if (vocab.length > 0 || tips.length > 0) {
      console.log(`[user-data] migrating ${vocab.length} vocab + ${tips.length} tips from Clerk for ${userId}`);
      await r2Put(userId, "vocab", vocab);
      await r2Put(userId, "tips",  tips);
      // Clear from Clerk to free up the 8KB slot
      await clerk.users.updateUser(userId, {
        privateMetadata: { vocab: [], tips: [], _migratedToR2: true },
      });
      console.log(`[user-data] migration complete for ${userId}`);
    }
    return { vocab, tips };
  } catch (e) {
    console.error("[user-data] migration error:", e.message);
    return { vocab: [], tips: [] };
  }
}

// ── Main handler ──────────────────────────────────────────────────────────────
export default async function handler(req, res) {
  // Auth
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
      // Read vocab + tips from R2
      let vocab = await r2Get(userId, "vocab");
      let tips  = await r2Get(userId, "tips");

      // First time — migrate from Clerk if data exists there
      if (vocab === null && tips === null) {
        const migrated = await migrateFromClerk(userId);
        vocab = migrated.vocab;
        tips  = migrated.tips;
      }

      return res.status(200).json({
        vocab: Array.isArray(vocab) ? vocab : [],
        tips:  Array.isArray(tips)  ? tips  : [],
      });
    }

    if (req.method === "POST") {
      const body = typeof req.body === "string" ? JSON.parse(req.body) : (req.body || {});

      // Handle different data types via ?type= param
      const type = req.query && req.query.type;

      if (type === "progress") {
        // Book reading progress: { [bookFilename]: { cidx, pidx, lastRead } }
        const progress = body.progress || {};
        await r2Put(userId, "progress", progress);
        return res.status(200).json({ ok: true });
      }

      if (type === "settings") {
        const settings = body.settings || {};
        await r2Put(userId, "settings", settings);
        return res.status(200).json({ ok: true });
      }

      // Default: vocab + tips (full objects, no stripping — R2 has no size limit)
      const vocab = Array.isArray(body.vocab) ? body.vocab : [];
      const tips  = Array.isArray(body.tips)  ? body.tips  : [];

      // Safety: never overwrite with empty (same guard as before)
      if (vocab.length === 0 && tips.length === 0) {
        return res.status(200).json({ ok: true, skipped: "empty payload" });
      }

      // Store full vocab entries — no field stripping needed
      const cleanVocab = vocab.map(function(v) {
        if (typeof v === "string") return { ru: v };
        if (!v || typeof v !== "object") return null;
        return v; // store everything as-is
      }).filter(Boolean);

      const cleanTips = tips.map(function(t) {
        if (typeof t === "string") return { tip: t, id: Date.now() };
        return t;
      }).filter(Boolean);

      await Promise.all([
        r2Put(userId, "vocab", cleanVocab),
        r2Put(userId, "tips",  cleanTips),
      ]);

      return res.status(200).json({
        ok: true,
        count: { vocab: cleanVocab.length, tips: cleanTips.length },
      });
    }

    return res.status(405).json({ error: "Method not allowed" });

  } catch (e) {
    const msg = e && e.message ? e.message : "Server error";
    console.error("[user-data] error:", msg);
    return res.status(500).json({ error: msg });
  }
}
