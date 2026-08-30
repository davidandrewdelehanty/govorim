// /api/user-data.js
// Stores per-user data in Cloudflare R2 (S3-compatible), keyed by user id.
// Auth: the site's own session cookie (see lib/auth.js).
// Storage: r2:govorim-audio/userdata/{userId}/{type}.json
// Separate files per data type: vocab, tips, progress, settings.
// No size limit (R2 has none).
//
// ── FORUM ────────────────────────────────────────────────────────────────────
// This function also serves the site forum (book requests / bug reports /
// general), folded in here rather than shipped as its own function so the
// deployment's serverless-function count stays put. vercel.json rewrites
//     /api/forum/:action  →  /api/user-data?forum=:action
// Storage, same bucket:
//     forum/<cat>/index.json   summary list, one CDN-cacheable read per board
//     forum/<cat>/<postId>.json  full post: body, votes, replies
// R2 has no transactions; every mutation is read-merge-write. Two writes in
// the same second can drop one of them — acceptable at this community's
// scale, and the index is always rebuilt from the post file it points at.
//
// The user id is derived from the email rather than random (lib/auth.js
// userIdFor), so a rebuilt account lands back on its own vocabulary.
// Accounts made under the old Clerk setup have their data under the old
// Clerk user id; /api/admin/import-userdata copies such a prefix across.
import { siteName } from "../lib/site.js";
import {
  S3Client, GetObjectCommand, PutObjectCommand
} from "@aws-sdk/client-s3";
import { requireUser, currentUser, bumpDaily, touchSeen } from "../lib/auth.js";
import { sendEmail } from "../lib/admin/helpers.js";
import { r2Endpoint } from "../lib/r2-endpoint.js";

const s3 = new S3Client({
  region: "auto",
  endpoint: r2Endpoint(),
  credentials: {
    accessKeyId:     process.env.R2_ACCESS_KEY_ID,
    secretAccessKey: process.env.R2_SECRET_ACCESS_KEY,
  },
});

const BUCKET = "govorim-audio";
// See lib/auth.js -- DATA_PREFIX namespaces the two deployments inside one
// bucket. Unset means govorim's original paths.
const DATA_PREFIX = (function () {
  const p = (process.env.DATA_PREFIX || "").trim().replace(/^\/+|\/+$/g, "");
  return p ? p + "/" : "";
})();

const PREFIX = DATA_PREFIX + "userdata";

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

// ── Main handler ──────────────────────────────────────────────────────────────
export default async function handler(req, res) {
  // ── Anonymous reading counter ───────────────────────────────────────────
  // Runs BEFORE the session check, because the whole point is the readers who
  // have no session. A signed-out reader keeps vocabulary, progress and the
  // rest in their own browser and none of it ever reaches the server, so the
  // only thing the site can know about them is a tally it is told. This
  // increments one number and stores nothing else — no identity, no address,
  // no title, nothing that says which reader or which book.
  //
  // It is unauthenticated, so it is inflatable by anyone who wants to spend an
  // afternoon POSTing to it. That is the price of counting people who have not
  // identified themselves, and it is why the panel labels this figure as
  // signed-out book opens rather than as readers.
  if (req.query && req.query.anon) {
    if (req.method !== "POST") return res.status(405).json({ error: "Method not allowed" });
    try {
      // Signed in or not decides which tallies this open belongs to. Read
      // rather than required: an unauthenticated open is the whole point.
      const who = currentUser(req);
      await bumpDaily("opens", 1);
      if (who) {
        // A thirty-day cookie hides how recently an account was really used.
        // Opening a book is a use; this records it, at most once a day.
        await touchSeen(who.email);
        return res.status(200).json({ ok: true });
      }
      await bumpDaily("anonOpens", 1);
      const key = `${PREFIX}/_stats/anon.json`;
      let cur = null;
      try {
        const resp = await s3.send(new GetObjectCommand({ Bucket: BUCKET, Key: key }));
        cur = JSON.parse(await resp.Body.transformToString());
      } catch (e) {
        if (!(e.name === "NoSuchKey" || e.$metadata?.httpStatusCode === 404)) throw e;
      }
      const next = {
        booksOpened: ((cur && cur.booksOpened) || 0) + 1,
        since: (cur && cur.since) || Date.now(),
      };
      // Read-merge-write with no transaction: two opens in the same instant can
      // lose one. Acceptable for a running tally nobody is billed against.
      await s3.send(new PutObjectCommand({
        Bucket: BUCKET, Key: key,
        Body: JSON.stringify(next), ContentType: "application/json",
      }));
      return res.status(200).json({ ok: true });
    } catch (e) {
      // Never let a counter break a page load.
      return res.status(200).json({ ok: false });
    }
  }

  const user = requireUser(req, res);
  if (!user) return;
  const userId = user.id;

  // ── Forum routes (rewritten from /api/forum/<action>) ──
  const forumAction = req.query && req.query.forum;
  if (forumAction) return handleForum(req, res, user, String(forumAction));

  try {
    if (req.method === "GET") {
      // Read vocab + tips from R2
      const vocab = await r2Get(userId, "vocab");
      const tips  = await r2Get(userId, "tips");
      // Books the reader has marked read, as { [bookKey]: {at, title, author} }.
      const finished = await r2Get(userId, "finished");

      return res.status(200).json({
        vocab: Array.isArray(vocab) ? vocab : [],
        tips:  Array.isArray(tips)  ? tips  : [],
        finished: (finished && typeof finished === "object" && !Array.isArray(finished)) ? finished : {},
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

      if (type === "finished") {
        // Books marked read: { [bookKey]: { at, title, author } }. Replaces the
        // stored map wholesale — the client holds the merged copy.
        const finished = body.finished;
        if (!finished || typeof finished !== "object" || Array.isArray(finished)) {
          return res.status(400).json({ error: "finished must be an object" });
        }
        await r2Put(userId, "finished", finished);
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

// ═════════════════════════════════════════════════════════════════════════════
// FORUM
// ═════════════════════════════════════════════════════════════════════════════

const FORUM_PREFIX = DATA_PREFIX + "forum";
const FORUM_CATS = ["requests", "bugs", "general"];
const MAX_TITLE = 120;
const MAX_BODY = 4000;
const MAX_REPLY = 2000;
const MAX_POSTS_PER_CAT = 500;    // index cap; oldest unpinned fall off

// Light per-user write limiter (in-memory, resets on cold start — a speed
// bump against accidental double-posts and scripts, not a security wall).
const forumWriteMap = new Map();
function forumWriteAllowed(userId) {
  const now = Date.now();
  const hits = (forumWriteMap.get(userId) || []).filter(function (t) { return now - t < 60000; });
  if (hits.length >= 10) return false;
  hits.push(now);
  forumWriteMap.set(userId, hits);
  return true;
}

async function forumGet(key) {
  try {
    const resp = await s3.send(new GetObjectCommand({ Bucket: BUCKET, Key: key }));
    return JSON.parse(await resp.Body.transformToString());
  } catch (e) {
    if (e.name === "NoSuchKey" || e.$metadata?.httpStatusCode === 404) return null;
    throw e;
  }
}

async function forumPut(key, data) {
  await s3.send(new PutObjectCommand({
    Bucket: BUCKET,
    Key: key,
    Body: JSON.stringify(data),
    ContentType: "application/json",
  }));
}

function catKey(cat)      { return `${FORUM_PREFIX}/${cat}/index.json`; }
function postKey(cat, id) { return `${FORUM_PREFIX}/${cat}/${id}.json`; }

// Display name: the part of the email before @. No profile system to consult.
function displayName(user) {
  const email = String(user.email || "");
  const at = email.indexOf("@");
  return at > 0 ? email.slice(0, at) : "reader";
}

function cleanText(t, max) {
  return String(t || "")
    .replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F]/g, "")
    .trim()
    .slice(0, max);
}

function newId() {
  return Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 8);
}

// The index entry is always derived from the post file, so a dropped index
// write heals on the next mutation of the same post.
function indexEntryOf(post) {
  return {
    id: post.id,
    title: post.title,
    authorName: post.authorName,
    createdAt: post.createdAt,
    replyCount: (post.replies || []).length,
    voteCount: (post.votes || []).length,
    pinned: !!post.pinned,
    closed: !!post.closed,
    lastActivity: post.lastActivity || post.createdAt,
  };
}

function sortIndex(posts) {
  posts.sort(function (a, b) {
    if (!!b.pinned - !!a.pinned) return (!!b.pinned) - (!!a.pinned);
    return (b.lastActivity || 0) - (a.lastActivity || 0);
  });
  return posts;
}

async function updateIndex(cat, post, remove) {
  const idx = (await forumGet(catKey(cat))) || { posts: [] };
  idx.posts = (idx.posts || []).filter(function (p) { return p.id !== post.id; });
  if (!remove) idx.posts.push(indexEntryOf(post));
  sortIndex(idx.posts);
  if (idx.posts.length > MAX_POSTS_PER_CAT) idx.posts.length = MAX_POSTS_PER_CAT;
  await forumPut(catKey(cat), idx);
  return idx;
}

// ── Email notifications ──────────────────────────────────────────────────────
// Every new post and reply mails the admin (FORUM_NOTIFY_EMAIL, falling back
// to ADMIN_EMAIL). Best-effort: a Resend hiccup never fails the request. The
// admin's own posts are skipped — no point mailing yourself about yourself.
const CAT_LABELS = { requests: "Book requests", bugs: "Bugs", general: "General" };

function escapeHtml(t) {
  return String(t || "").replace(/[&<>"]/g, function (ch) {
    return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch];
  });
}

async function notifyAdmin(user, subject, html) {
  const to = process.env.FORUM_NOTIFY_EMAIL || process.env.ADMIN_EMAIL;
  if (!to) return;
  if (user && String(user.email || "").toLowerCase() === String(to).toLowerCase()) return;
  try { await sendEmail({ to, subject, html }); } catch (_) { /* never blocks the post */ }
}

function postEmailHtml(post, cat) {
  return (
    "<p><strong>" + escapeHtml(post.authorName) + "</strong> in <strong>" +
    escapeHtml(CAT_LABELS[cat] || cat) + "</strong>:</p>" +
    "<h3 style=\"margin:6px 0\">" + escapeHtml(post.title) + "</h3>" +
    "<p style=\"white-space:pre-wrap\">" + escapeHtml(post.body) + "</p>" +
    "<p><a href=\"https://govorim.dev\">Open the forum</a></p>"
  );
}

async function handleForum(req, res, user, action) {
  try {
    // ---- reads ----
    if (action === "board") {
      if (req.method !== "GET") return res.status(405).json({ error: "Method not allowed" });
      const cat = String(req.query.cat || "");
      if (FORUM_CATS.indexOf(cat) === -1) return res.status(400).json({ error: "Unknown category" });
      const idx = (await forumGet(catKey(cat))) || { posts: [] };
      return res.status(200).json({ cat: cat, posts: sortIndex(idx.posts || []) });
    }

    if (action === "thread") {
      if (req.method !== "GET") return res.status(405).json({ error: "Method not allowed" });
      const cat = String(req.query.cat || "");
      const id = String(req.query.id || "");
      if (FORUM_CATS.indexOf(cat) === -1 || !id) return res.status(400).json({ error: "Bad request" });
      const post = await forumGet(postKey(cat, id));
      if (!post || post.deleted) return res.status(404).json({ error: "Post not found" });
      // The caller needs to know whether THEY voted; nobody needs the roster.
      const out = Object.assign({}, post, {
        voteCount: (post.votes || []).length,
        youVoted: (post.votes || []).indexOf(user.id) !== -1,
      });
      delete out.votes;
      return res.status(200).json(out);
    }

    // ---- writes ----
    if (req.method !== "POST") return res.status(405).json({ error: "Method not allowed" });
    if (!forumWriteAllowed(user.id)) {
      return res.status(429).json({ error: "Slow down a little — try again in a minute." });
    }
    let body = req.body;
    if (typeof body === "string") { try { body = JSON.parse(body); } catch { body = {}; } }
    body = body || {};
    const cat = String(body.cat || "");
    if (FORUM_CATS.indexOf(cat) === -1) return res.status(400).json({ error: "Unknown category" });

    if (action === "new") {
      const title = cleanText(body.title, MAX_TITLE);
      const text = cleanText(body.body, MAX_BODY);
      if (title.length < 3) return res.status(400).json({ error: "Title is too short" });
      if (text.length < 3) return res.status(400).json({ error: "Post body is too short" });
      const now = Date.now();
      const post = {
        id: newId(), cat: cat, title: title, body: text,
        authorId: user.id, authorName: displayName(user),
        createdAt: now, lastActivity: now,
        pinned: false, closed: false, votes: [], replies: [],
      };
      await forumPut(postKey(cat, post.id), post);
      await updateIndex(cat, post);
      await notifyAdmin(user, "[" + siteName() + " forum] " + (CAT_LABELS[cat] || cat) + ": " + post.title, postEmailHtml(post, cat));
      return res.status(200).json({ ok: true, id: post.id });
    }

    const id = String(body.id || "");
    if (!id) return res.status(400).json({ error: "Missing post id" });
    const post = await forumGet(postKey(cat, id));
    if (!post || post.deleted) return res.status(404).json({ error: "Post not found" });

    if (action === "reply") {
      if (post.closed && !user.isAdmin) return res.status(403).json({ error: "This thread is closed" });
      const text = cleanText(body.body, MAX_REPLY);
      if (text.length < 2) return res.status(400).json({ error: "Reply is too short" });
      post.replies = post.replies || [];
      post.replies.push({
        id: newId(), body: text,
        authorId: user.id, authorName: displayName(user),
        isAdmin: !!user.isAdmin, createdAt: Date.now(),
      });
      post.lastActivity = Date.now();
      await forumPut(postKey(cat, id), post);
      await updateIndex(cat, post);
      await notifyAdmin(user, "[" + siteName() + " forum] Reply on: " + post.title,
        "<p><strong>" + escapeHtml(user.email ? displayName(user) : "reader") + "</strong> replied in <strong>" +
        escapeHtml(CAT_LABELS[cat] || cat) + "</strong> to \u201c" + escapeHtml(post.title) + "\u201d:</p>" +
        "<p style=\"white-space:pre-wrap\">" + escapeHtml(text) + "</p>" +
        "<p><a href=\"https://govorim.dev\">Open the forum</a></p>");
      return res.status(200).json({ ok: true });
    }

    if (action === "vote") {
      post.votes = post.votes || [];
      const at = post.votes.indexOf(user.id);
      if (at === -1) post.votes.push(user.id); else post.votes.splice(at, 1);
      await forumPut(postKey(cat, id), post);
      await updateIndex(cat, post);
      return res.status(200).json({ ok: true, voteCount: post.votes.length, youVoted: at === -1 });
    }

    if (action === "mod") {
      if (!user.isAdmin) return res.status(403).json({ error: "Admin only" });
      const op = String(body.op || "");
      if (op === "pin")        post.pinned = true;
      else if (op === "unpin") post.pinned = false;
      else if (op === "close") post.closed = true;
      else if (op === "open")  post.closed = false;
      else if (op === "delete") post.deleted = true;
      else return res.status(400).json({ error: "Unknown mod op" });
      await forumPut(postKey(cat, id), post);
      await updateIndex(cat, post, op === "delete");
      return res.status(200).json({ ok: true });
    }

    return res.status(404).json({ error: "Unknown forum action" });
  } catch (e) {
    const msg = e && e.message ? e.message : "Server error";
    console.error("[forum] error:", msg);
    return res.status(500).json({ error: msg });
  }
}
