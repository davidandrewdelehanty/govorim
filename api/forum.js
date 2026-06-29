// /api/forum.js
// A tiny forum that lives entirely in Clerk privateMetadata.
//
// Each user has a `posts` array in their privateMetadata, each entry being either
// an "OP" (the start of a thread) or a "reply":
//
//   { tid: "<id>", op: true, title: "...", body: "...", ts: 12345 }   // an OP
//   { tid: "<id>", body: "...", ts: 12345 }                            // a reply
//
// To list/view threads, we fetch ALL approved users via getUserList(), gather
// every post across the userbase, and group by tid. Each post carries enough
// context to render the thread without a separate "author" join.
//
// Caps to fit Clerk's 8KB per-user metadata budget (shared with vocab + tips):
//   - 30 forum posts per user (FIFO drops oldest).
//   - Title ≤ 80 chars, body ≤ 1000 chars.

import { verifyToken, createClerkClient } from "@clerk/backend";

const clerk = createClerkClient({ secretKey: process.env.CLERK_SECRET_KEY });

const MAX_POSTS_PER_USER  = 30;
const MAX_TITLE_LEN       = 80;
const MAX_BODY_LEN        = 1000;

function isApproved(user, adminEmail) {
  return true; // approval gate removed
  const meta = (user && user.privateMetadata) || {};
  if (meta.approved === true) return true;
  const email = (user && user.primaryEmailAddress && user.primaryEmailAddress.emailAddress
    ? user.primaryEmailAddress.emailAddress
    : ""
  ).toLowerCase();
  if (adminEmail && email === adminEmail.toLowerCase()) return true;
  return false;
}

function displayName(user) {
  const first = (user && user.firstName) || "";
  const last  = (user && user.lastName)  || "";
  const name  = (first + " " + last).trim();
  if (name) return name;
  return (user && user.primaryEmailAddress && user.primaryEmailAddress.emailAddress) || "Unknown";
}

function looksLikeSizeError(err) {
  const m = ((err && err.message) || "").toLowerCase();
  return m.includes("size") || m.includes("limit") || m.includes("8192") || m.includes("payload");
}

function newThreadId() {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
}

// Walk every approved user's posts, return a flat list with author info embedded.
async function gatherAllPosts(adminEmail) {
  let list;
  try { list = await clerk.users.getUserList({ limit: 100 }); }
  catch (e) { return []; }
  const users = list && list.data ? list.data : list;
  const all = [];
  for (const u of users) {
    if (!isApproved(u, adminEmail)) continue;
    const posts = Array.isArray((u.privateMetadata || {}).posts) ? u.privateMetadata.posts : [];
    for (const p of posts) {
      if (!p || !p.tid) continue;
      all.push({
        tid:    p.tid,
        op:     !!p.op,
        title:  p.title || "",
        body:   p.body || "",
        ts:     p.ts || 0,
        author: { id: u.id, name: displayName(u) },
      });
    }
  }
  return all;
}

export default async function handler(req, res) {
  // Auth
  const authHeader = req.headers.authorization || "";
  const token = authHeader.startsWith("Bearer ") ? authHeader.slice(7) : "";
  if (!token) return res.status(401).json({ error: "Not signed in" });

  let userId;
  try {
    const payload = await verifyToken(token, { secretKey: process.env.CLERK_SECRET_KEY });
    userId = payload && payload.sub;
  } catch (_) { return res.status(401).json({ error: "Invalid token" }); }
  if (!userId) return res.status(401).json({ error: "No user in token" });

  const adminEmail = (process.env.ADMIN_EMAIL || "").trim();

  let me;
  try { me = await clerk.users.getUser(userId); }
  catch (_) { return res.status(401).json({ error: "User not found" }); }
  if (!isApproved(me, adminEmail)) return res.status(403).json({ error: "PENDING_APPROVAL" });

  // ── GET ─────────────────────────────────────────────────────────────────
  if (req.method === "GET") {
    const tid = (req.query && req.query.thread ? String(req.query.thread).trim() : "");
    const all = await gatherAllPosts(adminEmail);

    // Single thread view
    if (tid) {
      const posts = all.filter(function(p){ return p.tid === tid; })
                       .sort(function(a, b){ return a.ts - b.ts; });
      const op = posts.find(function(p){ return p.op; });
      if (!op) return res.status(404).json({ error: "Thread not found" });
      return res.status(200).json({
        thread: { tid: tid, title: op.title, author: op.author, ts: op.ts, posts: posts }
      });
    }

    // List view: group posts by tid, surface threads with their OP info.
    const byTid = {};
    for (const p of all) {
      if (!byTid[p.tid]) byTid[p.tid] = { tid: p.tid, op: null, replies: 0, lastTs: 0 };
      const t = byTid[p.tid];
      if (p.op) t.op = p;
      else t.replies += 1;
      if (p.ts > t.lastTs) t.lastTs = p.ts;
    }
    const threads = Object.values(byTid)
      .filter(function(t){ return t.op; })  // ignore reply-only tids (orphans)
      .map(function(t) {
        return {
          tid:     t.tid,
          title:   t.op.title,
          author:  t.op.author,
          ts:      t.op.ts,
          lastTs:  t.lastTs,
          replies: t.replies,
        };
      })
      .sort(function(a, b){ return b.lastTs - a.lastTs; });  // bumped by replies

    return res.status(200).json({ threads: threads });
  }

  // ── POST ────────────────────────────────────────────────────────────────
  if (req.method === "POST") {
    const body = typeof req.body === "string" ? JSON.parse(req.body) : (req.body || {});
    const isNewThread = body && typeof body.title === "string" && body.title.trim().length > 0 && !body.threadId;
    const isReply     = body && typeof body.threadId === "string" && body.threadId.trim().length > 0;
    if (!isNewThread && !isReply) return res.status(400).json({ error: "Bad request" });

    let post;
    if (isNewThread) {
      let title = String(body.title || "").trim();
      let text  = String(body.body  || "").trim();
      if (!title) return res.status(400).json({ error: "Title required" });
      if (!text)  return res.status(400).json({ error: "Body required" });
      if (title.length > MAX_TITLE_LEN) title = title.slice(0, MAX_TITLE_LEN);
      if (text.length  > MAX_BODY_LEN)  text  = text.slice(0,  MAX_BODY_LEN);
      post = { tid: newThreadId(), op: true, title: title, body: text, ts: Date.now() };
    } else {
      const tid = String(body.threadId).trim();
      let text  = String(body.body || "").trim();
      if (!text) return res.status(400).json({ error: "Body required" });
      if (text.length > MAX_BODY_LEN) text = text.slice(0, MAX_BODY_LEN);
      post = { tid: tid, body: text, ts: Date.now() };
    }

    const meMeta = me.privateMetadata || {};
    const existing = Array.isArray(meMeta.posts) ? meMeta.posts : [];
    let posts = existing.concat([post]);
    posts.sort(function(a, b){ return a.ts - b.ts; });
    while (posts.length > MAX_POSTS_PER_USER) posts.shift();

    try {
      await clerk.users.updateUser(userId, { privateMetadata: { posts: posts } });
    } catch (e) {
      if (looksLikeSizeError(e)) {
        while (posts.length > 15) posts.shift();
        try {
          await clerk.users.updateUser(userId, { privateMetadata: { posts: posts } });
        } catch (_) {
          return res.status(413).json({ error: "Storage full. Remove some vocab to free up space." });
        }
      } else {
        return res.status(500).json({ error: e.message || "Failed to save post" });
      }
    }

    return res.status(200).json({
      ok: true,
      post: {
        tid:   post.tid,
        op:    !!post.op,
        title: post.title || "",
        body:  post.body,
        ts:    post.ts,
        author: { id: userId, name: displayName(me) },
      }
    });
  }

  return res.status(405).json({ error: "Method not allowed" });
}
