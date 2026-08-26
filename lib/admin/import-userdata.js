// Copies one user's saved data from an old storage prefix to a new one.
//
// Vocabulary, tips, progress and settings are stored per user under
// userdata/<userId>/, and the ids issued by the old Clerk setup (user_2xyz…)
// are not the ids this site derives from an email. Rather than guess a
// mapping, this lets the admin move a prefix explicitly, once, after the
// account it belongs to has signed up again.
//
//   POST /api/admin/import-userdata
//   { "from": "user_2abc...", "toEmail": "someone@example.com" }
//
// Existing files at the destination are left alone unless overwrite:true --
// the failure worth avoiding here is replacing a live vocabulary list with
// an older copy.
import { requireAdmin } from "./helpers.js";
import { userIdFor } from "../auth.js";
import {
  S3Client, GetObjectCommand, PutObjectCommand,
} from "@aws-sdk/client-s3";
import { r2Endpoint } from "../r2-endpoint.js";

const BUCKET = process.env.R2_BUCKET || "govorim-audio";
const TYPES = ["vocab", "tips", "progress", "settings"];

let s3 = null;
function getS3() {
  if (!s3) {
    s3 = new S3Client({
      region: "auto",
      endpoint: r2Endpoint(),
      credentials: {
        accessKeyId: process.env.R2_ACCESS_KEY_ID,
        secretAccessKey: process.env.R2_SECRET_ACCESS_KEY,
      },
    });
  }
  return s3;
}

async function getJson(key) {
  try {
    const resp = await getS3().send(new GetObjectCommand({ Bucket: BUCKET, Key: key }));
    return JSON.parse(await resp.Body.transformToString());
  } catch (e) {
    if (e.name === "NoSuchKey" || e.$metadata?.httpStatusCode === 404) return null;
    throw e;
  }
}

async function putJson(key, data) {
  await getS3().send(new PutObjectCommand({
    Bucket: BUCKET,
    Key: key,
    Body: JSON.stringify(data, null, 2),
    ContentType: "application/json",
  }));
}

export async function handleImportUserdata(req, res) {
  if (req.method !== "POST") return res.status(405).json({ error: "Method not allowed" });
  const a = await requireAdmin(req, res);
  if (!a) return;

  let body = req.body;
  if (typeof body === "string") {
    try { body = JSON.parse(body); } catch { body = {}; }
  }
  const from = String((body && body.from) || "").trim();
  const toEmail = String((body && body.toEmail) || "").trim();
  const overwrite = !!(body && body.overwrite);
  if (!from || !toEmail) {
    return res.status(400).json({ error: "Need both 'from' (old user id) and 'toEmail'" });
  }
  if (from.includes("/")) return res.status(400).json({ error: "'from' should be a user id, not a path" });

  const to = userIdFor(toEmail);
  if (to === from) return res.status(400).json({ error: "Source and destination are the same" });

  const moved = [];
  const skipped = [];
  try {
    for (const type of TYPES) {
      const src = await getJson(`userdata/${from}/${type}.json`);
      if (src === null) { skipped.push({ type, reason: "not present at source" }); continue; }
      if (!overwrite && (await getJson(`userdata/${to}/${type}.json`)) !== null) {
        skipped.push({ type, reason: "already exists at destination" });
        continue;
      }
      await putJson(`userdata/${to}/${type}.json`, src);
      moved.push({ type, items: Array.isArray(src) ? src.length : undefined });
    }
    return res.status(200).json({ ok: true, from, to, toEmail, moved, skipped });
  } catch (err) {
    return res.status(500).json({ error: "Import failed: " + (err.message || err), moved, skipped });
  }
}
