// The gate in front of restricted books.
//
// Two kinds of asset, two mechanisms:
//
//   ?path=novel/patriot.fb2      text and alignment JSON, read from
//                                private/books/ (bundled into this function,
//                                never served as a static asset) and returned
//                                only to the admin.
//
//   ?audio=patriot/01.mp3        audio, which is far too big to proxy through
//                                a serverless function on every seek. Instead
//                                the object lives in a PRIVATE R2 bucket and
//                                this returns a redirect to a presigned URL
//                                valid for a few minutes.
//
// Why the private bucket matters: govorim-audio is public through its r2.dev
// domain, so an object in it is readable by anyone who knows the key --
// hiding a book in the UI would not protect the recording. Moving the
// restricted books' objects into a bucket with no public access is what
// makes the gate real. scripts/gate-books.sh does the move.

import fs from "node:fs";
import path from "node:path";
import { S3Client, GetObjectCommand } from "@aws-sdk/client-s3";
import { getSignedUrl } from "@aws-sdk/s3-request-presigner";
import { requireAdminUser } from "../lib/auth.js";

const PRIVATE_BUCKET = process.env.R2_PRIVATE_BUCKET || "govorim-private";
const URL_TTL_SECONDS = 15 * 60;

const TYPES = {
  ".json": "application/json; charset=utf-8",
  ".fb2": "application/xml; charset=utf-8",
  ".txt": "text/plain; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".xhtml": "application/xhtml+xml; charset=utf-8",
  ".epub": "application/epub+zip",
  ".zip": "application/zip",
};

let s3 = null;
function getS3() {
  if (!s3) {
    s3 = new S3Client({
      region: "auto",
      endpoint: process.env.R2_ENDPOINT,
      credentials: {
        accessKeyId: process.env.R2_ACCESS_KEY_ID,
        secretAccessKey: process.env.R2_SECRET_ACCESS_KEY,
      },
    });
  }
  return s3;
}

// Reject anything that could climb out of private/books/: a leading slash,
// a drive letter, a .. segment, or a backslash pretending to be a separator.
function safeRelPath(raw) {
  const value = String(raw || "").replace(/\\/g, "/");
  if (!value || value.startsWith("/") || /^[a-zA-Z]:/.test(value)) return null;
  if (value.split("/").some(function (seg) { return seg === ".." || seg === "."; })) return null;
  return value;
}

export default async function handler(req, res) {
  const user = requireAdminUser(req, res);
  if (!user) return;

  const rawPath = Array.isArray(req.query.path) ? req.query.path[0] : req.query.path;
  const rawAudio = Array.isArray(req.query.audio) ? req.query.audio[0] : req.query.audio;

  if (rawAudio) {
    const key = safeRelPath(rawAudio);
    if (!key) return res.status(400).json({ error: "Bad audio key" });
    if (!process.env.R2_ENDPOINT || !process.env.R2_ACCESS_KEY_ID) {
      return res.status(500).json({ error: "R2 credentials not configured" });
    }
    try {
      const url = await getSignedUrl(
        getS3(),
        new GetObjectCommand({ Bucket: PRIVATE_BUCKET, Key: key }),
        { expiresIn: URL_TTL_SECONDS },
      );
      res.setHeader("Cache-Control", "private, no-store");
      res.redirect(302, url);
      return;
    } catch (e) {
      return res.status(500).json({ error: "Could not sign audio URL: " + (e.message || e) });
    }
  }

  const rel = safeRelPath(rawPath);
  if (!rel) return res.status(400).json({ error: "Bad path" });

  const root = path.join(process.cwd(), "private", "books");
  const full = path.join(root, rel);
  // Belt and braces: even with the segment checks above, confirm the
  // resolved path is still inside the private book root.
  if (!full.startsWith(root + path.sep)) {
    return res.status(400).json({ error: "Bad path" });
  }

  let data;
  try {
    data = fs.readFileSync(full);
  } catch {
    return res.status(404).json({ error: "Not found" });
  }

  res.setHeader("Content-Type", TYPES[path.extname(full).toLowerCase()] || "application/octet-stream");
  res.setHeader("Cache-Control", "private, no-store");
  res.status(200).send(data);
}
