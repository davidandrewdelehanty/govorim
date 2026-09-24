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
import { siteName, isPublicSite } from "../lib/site.js";
import fs from "node:fs";
import path from "node:path";
import {
  S3Client, GetObjectCommand, PutObjectCommand
} from "@aws-sdk/client-s3";
import { requireUser, currentUser, bumpDaily, touchSeen, findAccount,
  updateBoardRow, readBoards, learnedCount, finishedCount, wordsRead } from "../lib/auth.js";
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

// Every YouTube id the music manifests carry, read once per cold start. Both
// files are consulted rather than the one this deployment serves: the two sites
// share a bucket, and a song counted under one should not be refused under the
// other for the sake of a file name.
let SONG_IDS = null;
function knownSongIds() {
  if (SONG_IDS) return SONG_IDS;
  const ids = new Set();
  for (const name of ["music.json", "music.public.json"]) {
    try {
      const j = JSON.parse(fs.readFileSync(
        path.join(process.cwd(), "public", "music", name), "utf8"));
      for (const artist of (Array.isArray(j) ? j : [])) {
        for (const song of ((artist && artist.songs) || [])) {
          const y = String((song && song.youtube) || "").trim();
          if (/^[A-Za-z0-9_-]{11}$/.test(y)) ids.add(y);
        }
      }
    } catch (e) { /* a missing manifest just means no ids from it */ }
  }
  SONG_IDS = ids;
  return ids;
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
    // The public count, for the footer. Readable by anyone, because it is
    // shown to everyone — a running total and the date it started, and
    // nothing that says who any of those visits belonged to.
    // Funding: the running cost of the site and what has come in against it.
    // Public because the progress is shown to everyone, and because the point
    // of showing it is to stop asking once the costs are met.
    if (req.query.anon === "funding" && req.method === "GET") {
      try {
        const resp = await s3.send(new GetObjectCommand({
          Bucket: BUCKET, Key: `${PREFIX}/_stats/funding.json`,
        }));
        const f = JSON.parse(await resp.Body.transformToString());
        res.setHeader("Cache-Control", "public, max-age=300, s-maxage=300");
        return res.status(200).json({
          goal: f.goal || 0, raised: f.raised || 0,
          period: f.period || "", note: f.note || "", updatedAt: f.updatedAt || null,
        });
      } catch (e) {
        return res.status(200).json({ goal: 0, raised: 0 });
      }
    }
    // The library's own weather: how often each title has been opened, and
    // how often each song has been played. Public because it describes the
    // shelf rather than anyone standing at it — a filename and a number, with
    // no way to tell one reader from a hundred. Cached hard: it changes by one
    // every few minutes and nobody needs it to the second.
    // The leaderboards: words retired through practice, and books marked read.
    // Public, like the popularity list — and only readers who have chosen a
    // username appear, so nobody is on it by their email.
    if (req.query.anon === "boards" && req.method === "GET") {
      try {
        const out = await readBoards(100);
        res.setHeader("Cache-Control", "public, s-maxage=60, stale-while-revalidate=300");
        return res.status(200).json(out);
      } catch (e) {
        return res.status(200).json({ learned: [], words: [], read: [],
                                      error: "unavailable", note: e.message || String(e) });
      }
    }

    if (req.query.anon === "books" && req.method === "GET") {
      try {
        const grab = async function (name) {
          try {
            const r = await s3.send(new GetObjectCommand({
              Bucket: BUCKET, Key: `${PREFIX}/_stats/${name}.json`,
            }));
            const j = JSON.parse(await r.Body.transformToString());
            return (j && typeof j === "object") ? j : {};
          } catch (e) { return {}; }
        };
        const [books, songs, anon] = await Promise.all([
          grab("books"), grab("songs"), grab("anon"),
        ]);
        res.setHeader("Cache-Control", "public, max-age=300, s-maxage=300");
        return res.status(200).json({
          opens: books, songs: songs, since: anon.since || null,
        });
      } catch (e) {
        return res.status(200).json({ opens: {}, songs: {}, since: null });
      }
    }
    if (req.query.anon === "count" && req.method === "GET") {
      try {
        const resp = await s3.send(new GetObjectCommand({
          Bucket: BUCKET, Key: `${PREFIX}/_stats/site.json`,
        }));
        const cur = JSON.parse(await resp.Body.transformToString());
        res.setHeader("Cache-Control", "public, max-age=300, s-maxage=300");
        return res.status(200).json({ visits: cur.visits || 0, since: cur.since || null });
      } catch (e) {
        return res.status(200).json({ visits: 0, since: null });
      }
    }
    if (req.method !== "POST") return res.status(405).json({ error: "Method not allowed" });
    // ── A video that would not play ─────────────────────────────────────
    // The chapter player reports when YouTube refuses it (embedding turned
    // off, video deleted or private), so a dead recording is known the first
    // time a reader hits it rather than whenever someone thinks to sweep.
    //
    // This endpoint cannot require a session — signed-out readers hit dead
    // videos too — so it is built to be unspammable: the id must be a video
    // actually in the catalogue (checked against the manifest), and each id
    // mails at most once, ever, via a dedupe file. An attacker can at worst
    // send one email per genuinely catalogued video, which is the email you
    // wanted anyway.
    if (req.query.anon === "embederr") {
      try {
        let body = req.body;
        if (typeof body === "string") { try { body = JSON.parse(body); } catch { body = {}; } }
        body = body || {};
        const v = String(body.v || "").trim();
        const code = parseInt(body.code, 10) || 0;
        const where = String(body.where || "").slice(0, 200);
        if (!/^[A-Za-z0-9_-]{11}$/.test(v)) return res.status(200).json({ ok: false });
        // Only ids the catalogue actually carries.
        let manifest = [];
        try {
          manifest = JSON.parse(fs.readFileSync(
            path.join(process.cwd(), "private", "books", "index.json"), "utf8"));
        } catch (e) {}
        const known = new Set();
        for (const b of manifest) {
          for (const k of Object.keys(b.videos || {})) {
            const y = String((b.videos[k] || {}).youtube || "");
            if (y) known.add(y);
          }
          for (const u of (b.songs || [])) {
            const m = String(u || "").match(/([A-Za-z0-9_-]{11})/);
            if (m) known.add(m[1]);
          }
        }
        if (!known.has(v)) return res.status(200).json({ ok: false });
        // Once per video, ever.
        const key = `${PREFIX}/_stats/embed-errors.json`;
        let seen = null;
        try {
          const r2 = await s3.send(new GetObjectCommand({ Bucket: BUCKET, Key: key }));
          seen = JSON.parse(await r2.Body.transformToString());
        } catch (e) {
          if (!(e.name === "NoSuchKey" || e.$metadata?.httpStatusCode === 404)) throw e;
        }
        seen = (seen && typeof seen === "object") ? seen : {};
        if (seen[v]) return res.status(200).json({ ok: true, dedup: true });
        seen[v] = { at: Date.now(), code, where };
        await s3.send(new PutObjectCommand({
          Bucket: BUCKET, Key: key,
          Body: JSON.stringify(seen, null, 2), ContentType: "application/json",
        }));
        const to = process.env.FORUM_NOTIFY_EMAIL || process.env.ADMIN_EMAIL;
        if (to) {
          const meaning = { 101: "embedding disabled by the uploader",
                            150: "embedding disabled by the uploader",
                            100: "video removed or private",
                            2: "malformed video id", 5: "player error" }[code] || ("error code " + code);
          await sendEmail({
            to,
            subject: siteName() + ": a recording will not play — " + v,
            html: "<p>A reader hit a video that refused to play.</p>" +
              "<p><b>Video:</b> <a href=\"https://www.youtube.com/watch?v=" + v + "\">" + v + "</a><br>" +
              "<b>Why:</b> " + meaning + " (code " + code + ")<br>" +
              "<b>Where:</b> " + escapeHtml(where || "unknown") + "</p>" +
              "<p>This mails once per video. The row in _stats/embed-errors.json remembers it was sent.</p>",
          });
        }
        return res.status(200).json({ ok: true });
      } catch (e) {
        return res.status(200).json({ ok: false });
      }
    }
    // ── Which donate button gets pressed ───────────────────────────────
    // Two buttons ask for money and they ask for different things: one sends
    // readers to Memorial for political prisoners, the other covers this
    // site's bills. Knowing which one people actually press is the only way
    // to tell whether the Memorial link is doing anything or is just decoration
    // above a PayPal form.
    //
    // This records the CLICK, not the donation — neither PayPal nor Memorial
    // tells this site what happened after the reader left, so a press here
    // means intent and nothing more, and the panel says so. Unauthenticated,
    // like every counter on this route, because signed-out readers donate too;
    // the value is clamped to the two known buttons so the file cannot be
    // filled with junk keys.
    if (req.query.anon === "donateclick") {
      try {
        let body = req.body;
        if (typeof body === "string") { try { body = JSON.parse(body); } catch { body = {}; } }
        const which = String((body || {}).which || "");
        if (which !== "memorial" && which !== "costs") {
          return res.status(200).json({ ok: false });
        }
        await bumpDaily(which === "memorial" ? "donateMemorial" : "donateCosts", 1);
        const key = `${PREFIX}/_stats/donate-clicks.json`;
        let cur = null;
        try {
          const resp = await s3.send(new GetObjectCommand({ Bucket: BUCKET, Key: key }));
          cur = JSON.parse(await resp.Body.transformToString());
        } catch (e) {
          if (!(e.name === "NoSuchKey" || e.$metadata?.httpStatusCode === 404)) throw e;
        }
        cur = (cur && typeof cur === "object") ? cur : {};
        cur[which] = (cur[which] || 0) + 1;
        cur.since = cur.since || Date.now();
        await s3.send(new PutObjectCommand({
          Bucket: BUCKET, Key: key,
          Body: JSON.stringify(cur, null, 2), ContentType: "application/json",
        }));
        return res.status(200).json({ ok: true });
      } catch (e) {
        return res.status(200).json({ ok: false });
      }
    }
    // A song opened in the Music tab. The books tally has always answered
    // "which of these does anyone actually read"; this asks it of the music,
    // which until now was shipped blind.
    //
    // Keyed by the YouTube id rather than the title: the id is the one field
    // that survives a retitling or a change of spelling, and it is eleven
    // characters of a fixed alphabet, which makes it safe as a key. Only ids
    // the music manifest actually carries are counted — the same guard the
    // dead-embed report uses — so an unauthenticated endpoint cannot be used
    // to grow the file with ids nobody ships.
    if (req.query.anon === "song") {
      try {
        const v = String((req.query && req.query.s) || "").trim();
        if (!/^[A-Za-z0-9_-]{11}$/.test(v)) return res.status(200).json({ ok: false });
        if (!knownSongIds().has(v)) return res.status(200).json({ ok: false });
        await bumpDaily("songOpens", 1);
        const key = `${PREFIX}/_stats/songs.json`;
        let cur = null;
        try {
          const resp = await s3.send(new GetObjectCommand({ Bucket: BUCKET, Key: key }));
          cur = JSON.parse(await resp.Body.transformToString());
        } catch (e) {
          if (!(e.name === "NoSuchKey" || e.$metadata?.httpStatusCode === 404)) throw e;
        }
        cur = (cur && typeof cur === "object") ? cur : {};
        cur[v] = (cur[v] || 0) + 1;
        await s3.send(new PutObjectCommand({
          Bucket: BUCKET, Key: key,
          Body: JSON.stringify(cur), ContentType: "application/json",
        }));
        return res.status(200).json({ ok: true });
      } catch (e) {
        return res.status(200).json({ ok: false });
      }
    }
    // A visit, as against a book opening. Fired once per browser per day by
    // the client, so this counts people arriving rather than pages rendered —
    // a number that goes up when someone comes back tomorrow, not when they
    // click twice. Stores a running total and a per-day figure, nothing else.
    if (req.query.anon === "visit") {
      try {
        const who = currentUser(req);
        await bumpDaily("visits", 1);
        if (!who) await bumpDaily("anonVisits", 1);
        const key = `${PREFIX}/_stats/site.json`;
        let cur = null;
        try {
          const resp = await s3.send(new GetObjectCommand({ Bucket: BUCKET, Key: key }));
          cur = JSON.parse(await resp.Body.transformToString());
        } catch (e) {
          if (!(e.name === "NoSuchKey" || e.$metadata?.httpStatusCode === 404)) throw e;
        }
        await s3.send(new PutObjectCommand({
          Bucket: BUCKET, Key: key,
          Body: JSON.stringify({
            visits: ((cur && cur.visits) || 0) + 1,
            since: (cur && cur.since) || Date.now(),
          }),
          ContentType: "application/json",
        }));
        return res.status(200).json({ ok: true });
      } catch (e) {
        return res.status(200).json({ ok: false });
      }
    }
    try {
      // Signed in or not decides which tallies this open belongs to. Read
      // rather than required: an unauthenticated open is the whole point.
      const who = currentUser(req);
      await bumpDaily("opens", 1);
      // Which book, so the panel can rank them. A filename, not a reader —
      // this counter says "Дубровский was opened 41 times", never who by.
      // Sanitised and capped: it becomes a key in a JSON file, and the value
      // arrives from the open internet.
      // \w is ASCII-only in JavaScript, so the first version of this filter
      // deleted every Cyrillic letter: «novel/Chekhov - Chayka.fb2» in its real
      // spelling arrived as «novel/ - .fb2», and every Cyrillic-named file in
      // the library piled into one meaningless row in the admin panel. The
      // Cyrillic block is allowed explicitly now. The filter exists to keep
      // control characters and path tricks out of an R2 key, not to insist the
      // alphabet be Latin.
      const raw = String((req.query && req.query.b) || "");
      const bookKey = raw
        .replace(/[^\w\u0400-\u04FF.\/\-\u2013\u2014\u00AB\u00BB() ]+/g, "")
        .replace(/\.{2,}/g, ".")
        .slice(0, 160);
      if (bookKey) {
        try {
          const bk = `${PREFIX}/_stats/books.json`;
          let books = null;
          try {
            const r2 = await s3.send(new GetObjectCommand({ Bucket: BUCKET, Key: bk }));
            books = JSON.parse(await r2.Body.transformToString());
          } catch (e) {
            if (!(e.name === "NoSuchKey" || e.$metadata?.httpStatusCode === 404)) throw e;
          }
          books = (books && typeof books === "object") ? books : {};
          // A cap on distinct keys, so a bad actor posting junk filenames
          // cannot grow this file without bound. Known books keep counting.
          if (books[bookKey] !== undefined || Object.keys(books).length < 400) {
            books[bookKey] = (books[bookKey] || 0) + 1;
            await s3.send(new PutObjectCommand({
              Bucket: BUCKET, Key: bk,
              Body: JSON.stringify(books), ContentType: "application/json",
            }));
          }
        } catch (e) { /* the tally must not break the opening */ }
      }
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

  // Any authenticated call is the reader being present. A page load touches
  // this through /api/auth/me, but a tab left open all afternoon never loads
  // again — it just goes on saving progress and vocabulary through here, and
  // without this that reader would look last-seen at whatever time they
  // opened the tab. touchSeen throttles itself, so this costs a read.
  //
  // Awaited, not fired and forgotten: this runs on a serverless function that
  // can be frozen the moment the response is sent, and a dangling promise
  // would lose the write it was supposed to make.
  try { await touchSeen(user.email); } catch (e) {}

  // ── Forum routes (rewritten from /api/forum/<action>) ──
  const forumAction = req.query && req.query.forum;
  if (forumAction) return handleForum(req, res, user, String(forumAction));

  // ── Group reads (?group=<action>) ──
  const groupAction = req.query && req.query.group;
  if (groupAction) return handleGroup(req, res, user, String(groupAction));

  // A chat belongs to a group read and to nothing else, so ?chat= — the
  // site-wide reading room — is gone. A reader still on an old build gets a
  // plain answer rather than a crash.
  if (req.query && req.query.chat) {
    return res.status(410).json({ error: "The reading room has closed — chat lives in group reads now." });
  }

  try {
    if (req.method === "GET") {
      // Read vocab + tips from R2
      const vocab = await r2Get(userId, "vocab");
      const tips  = await r2Get(userId, "tips");
      // Books the reader has marked read, as { [bookKey]: {at, title, author} }.
      const finished = await r2Get(userId, "finished");
      // Words retired from the active list by the spaced-repetition scheduler,
      // and the day-by-day reading and practice log behind the streak.
      const learned = await r2Get(userId, "learned");
      const stats = await r2Get(userId, "stats");
      // Songs opened in the Music tab, and finished case drills. Both used to
      // live only in the browser, so both read empty for every account that
      // predates this — which is a gap in the record, not a reader who never
      // did either.
      const songs = await r2Get(userId, "songs");
      const drills = await r2Get(userId, "drills");
      // Highlights, notes and pen strokes: { items: { [id]: item } }.
      const annots = await r2Get(userId, "annots");

      return res.status(200).json({
        vocab: Array.isArray(vocab) ? vocab : [],
        tips:  Array.isArray(tips)  ? tips  : [],
        finished: (finished && typeof finished === "object" && !Array.isArray(finished)) ? finished : {},
        learned: Array.isArray(learned) ? learned : [],
        stats: (stats && typeof stats === "object" && !Array.isArray(stats)) ? stats : {},
        songs: (songs && typeof songs === "object" && !Array.isArray(songs)) ? songs : {},
        drills: (drills && typeof drills === "object" && !Array.isArray(drills)) ? drills : {},
        annots: (annots && typeof annots === "object" && annots.items) ? annots : { items: {} },
      });
    }

    if (req.method === "POST") {
      const body = typeof req.body === "string" ? JSON.parse(req.body) : (req.body || {});

      // Handle different data types via ?type= param
      const type = req.query && req.query.type;

      if (type === "progress") {
        // Book reading progress: { [bookFilename]: { cidx, pidx, lastRead } }.
        // Merged per book rather than replaced wholesale: each device pushes
        // only the books IT has opened, so a phone with one book would
        // otherwise erase the twenty a laptop had reported. Per key, the
        // newer lastRead wins.
        const progress = body.progress || {};
        let existing = null;
        try { existing = await r2Get(userId, "progress"); } catch (e) {}
        const merged = (existing && typeof existing === "object" && !Array.isArray(existing)) ? existing : {};
        for (const k of Object.keys(progress)) {
          const inc = progress[k];
          const cur = merged[k];
          if (!cur || ((inc && inc.lastRead) || 0) >= ((cur && cur.lastRead) || 0)) merged[k] = inc;
        }
        await r2Put(userId, "progress", merged);
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
        await noteBoard(user, { read: finishedCount(finished) });
        return res.status(200).json({ ok: true });
      }

      if (type === "stats") {
        // Daily reading/practice log: { "2026-09-01": { read, practiced } }.
        // Merged per day, larger figure wins: each device only saw its own
        // sessions, and two devices reading on one day would otherwise take
        // turns erasing each other's count.
        const inc = body.stats;
        if (!inc || typeof inc !== "object" || Array.isArray(inc)) {
          return res.status(400).json({ error: "stats must be an object" });
        }
        let existing = null;
        try { existing = await r2Get(userId, "stats"); } catch (e) {}
        const merged = (existing && typeof existing === "object" && !Array.isArray(existing)) ? existing : {};
        for (const k of Object.keys(inc)) {
          if (!/^\d{4}-\d{2}-\d{2}$/.test(k)) continue;
          const a = merged[k] || {}, b = inc[k] || {};
          merged[k] = {
            read: Math.max(Number(a.read) || 0, Number(b.read) || 0),
            practiced: Math.max(Number(a.practiced) || 0, Number(b.practiced) || 0),
          };
        }
        await r2Put(userId, "stats", merged);
        await noteBoard(user, { words: wordsRead(merged) });
        return res.status(200).json({ ok: true, stats: merged });
      }

      if (type === "learned") {
        // Retired vocabulary. Replaced wholesale, like vocab: the client holds
        // the merged copy, and an empty list is refused for the same reason.
        const learned = body.learned;
        if (!Array.isArray(learned)) return res.status(400).json({ error: "learned must be an array" });
        if (learned.length === 0 && body.allowEmpty !== true) {
          return res.status(200).json({ ok: true, skipped: "empty payload" });
        }
        await r2Put(userId, "learned", learned);
        await noteBoard(user, { learned: learnedCount(learned) });
        return res.status(200).json({ ok: true });
      }

      if (type === "annots") {
        // A reader's own annotations. Merged per item on updatedAt, so each
        // device's newest edit to each highlight wins and a deletion (a
        // tombstone with deleted:true) beats an older copy of the same item.
        const inc = body.items;
        if (!inc || typeof inc !== "object" || Array.isArray(inc)) {
          return res.status(400).json({ error: "items must be an object" });
        }
        let existing = null;
        try { existing = await r2Get(userId, "annots"); } catch (e) {}
        const items = (existing && existing.items && typeof existing.items === "object") ? existing.items : {};
        let n = 0;
        for (const k of Object.keys(inc)) {
          if (++n > 5000) break;
          const it = cleanAnnot(inc[k]);
          if (!it || it.id !== k) continue;
          const cur = items[k];
          if (!cur || (it.updatedAt || 0) >= (cur.updatedAt || 0)) items[k] = it;
        }
        await r2Put(userId, "annots", { items });
        return res.status(200).json({ ok: true, count: Object.keys(items).length });
      }

      if (type === "songs") {
        // Songs opened in the Music tab, as
        //   { [youtubeId]: { n, at, artist, title } }.
        // Merged per song: n takes the larger count and `at` the later visit,
        // for the same reason progress is merged — each device saw only its
        // own listening, and a phone with one song would otherwise erase the
        // twenty a laptop had.
        const inc = body.songs;
        if (!inc || typeof inc !== "object" || Array.isArray(inc)) {
          return res.status(400).json({ error: "songs must be an object" });
        }
        let existing = null;
        try { existing = await r2Get(userId, "songs"); } catch (e) {}
        const merged = (existing && typeof existing === "object" && !Array.isArray(existing)) ? existing : {};
        for (const k of Object.keys(inc)) {
          if (!/^[A-Za-z0-9_-]{11}$/.test(k)) continue;
          const a = merged[k] || {}, b = inc[k] || {};
          merged[k] = {
            n: Math.max(Number(a.n) || 0, Number(b.n) || 0),
            at: Math.max(Number(a.at) || 0, Number(b.at) || 0),
            artist: String(b.artist || a.artist || "").slice(0, 120),
            title: String(b.title || a.title || "").slice(0, 160),
          };
        }
        await r2Put(userId, "songs", merged);
        return res.status(200).json({ ok: true });
      }

      if (type === "drills") {
        // Case drills finished, as
        //   { runs, questions, correct, last, byBook: { [key]: {...} } }.
        // Counters only ever go up, so the larger figure wins a merge — the
        // same rule the daily reading log uses, and for the same reason.
        const inc = body.drills;
        if (!inc || typeof inc !== "object" || Array.isArray(inc)) {
          return res.status(400).json({ error: "drills must be an object" });
        }
        let existing = null;
        try { existing = await r2Get(userId, "drills"); } catch (e) {}
        const cur = (existing && typeof existing === "object" && !Array.isArray(existing)) ? existing : {};
        const big = function (a, b) { return Math.max(Number(a) || 0, Number(b) || 0); };
        const merged = {
          runs: big(cur.runs, inc.runs),
          questions: big(cur.questions, inc.questions),
          correct: big(cur.correct, inc.correct),
          last: big(cur.last, inc.last),
          byBook: Object.assign({}, cur.byBook || {}),
        };
        const inBooks = (inc.byBook && typeof inc.byBook === "object") ? inc.byBook : {};
        for (const k of Object.keys(inBooks).slice(0, 400)) {
          const a = merged.byBook[k] || {}, b = inBooks[k] || {};
          merged.byBook[String(k).slice(0, 200)] = {
            runs: big(a.runs, b.runs),
            questions: big(a.questions, b.questions),
            correct: big(a.correct, b.correct),
            title: String(b.title || a.title || "").slice(0, 160),
          };
        }
        await r2Put(userId, "drills", merged);
        return res.status(200).json({ ok: true, drills: merged });
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

// ── Annotations ───────────────────────────────────────────────────────────────
//
// One shape for both layers, personal and group. It follows the W3C Web
// Annotation model that Recogito and Apache Annotator use: a highlight is
// anchored by POSITION (start/end in the chapter's own character offsets —
// the same coordinates the reader's word spans carry) and by QUOTE (the words
// themselves), so if a book's text is ever corrected and the offsets move,
// the quote is what finds the passage again. A pen stroke is anchored to the
// paragraph it was drawn on, with its points as fractions of that
// paragraph's box, so it stays with its paragraph when the page reflows.
const ANNOT_COLORS = new Set(["yellow", "green", "blue", "pink", "ink"]);
function num(v, lo, hi) {
  const n = Number(v);
  if (!isFinite(n)) return null;
  return Math.min(hi, Math.max(lo, n));
}
function cleanAnnot(raw) {
  if (!raw || typeof raw !== "object") return null;
  const id = String(raw.id || "");
  if (!/^[A-Za-z0-9_-]{6,40}$/.test(id)) return null;
  const kind = raw.kind === "ink" ? "ink" : raw.kind === "hl" ? "hl" : null;
  if (!kind) return null;
  const out = {
    id, kind,
    bookKey: String(raw.bookKey || "").slice(0, 300),
    cidx: Math.floor(num(raw.cidx, 0, 100000) || 0),
    color: ANNOT_COLORS.has(raw.color) ? raw.color : (kind === "ink" ? "ink" : "yellow"),
    createdAt: Math.floor(num(raw.createdAt, 0, 9e15) || Date.now()),
    updatedAt: Math.floor(num(raw.updatedAt, 0, 9e15) || Date.now()),
  };
  if (raw.deleted) { out.deleted = true; return out; }
  if (kind === "hl") {
    const s = Math.floor(num(raw.start, 0, 1e8)), e = Math.floor(num(raw.end, 0, 1e8));
    if (s === null || e === null || e <= s || e - s > 20000) return null;
    out.start = s; out.end = e;
    out.quote = String(raw.quote || "").slice(0, 600);
    out.note = String(raw.note || "").slice(0, 2000);
  } else {
    out.paraStart = Math.floor(num(raw.paraStart, 0, 1e8) || 0);
    out.size = num(raw.size, 1, 24) || 3;
    const pts = Array.isArray(raw.points) ? raw.points.slice(0, 800) : [];
    out.points = [];
    for (const p of pts) {
      if (!Array.isArray(p)) continue;
      const x = num(p[0], -0.5, 1.5), y = num(p[1], -0.5, 1.5);
      if (x === null || y === null) continue;
      out.points.push([Math.round(x * 10000) / 10000, Math.round(y * 10000) / 10000]);
    }
    if (out.points.length < 2) return null;
  }
  return out;
}

// ── Group reads ──────────────────────────────────────────────────────────────

const GROUPS = `${PREFIX}/_groups`;
const GROUP_ITEM_CAP = 4000;
const GROUP_CHAT_CAP = 400;

// The reader's row on the leaderboards, with their current name and avatar
// carried along so the board never has to look an account up to draw it.
// Best-effort: a board that is a save behind is better than a failed save.
async function noteBoard(user, counts) {
  try {
    const account = await findAccount(user.email).catch(function () { return null; });
    await updateBoardRow(user.id, Object.assign({
      name: (account && account.username) || "",
      avatar: (account && account.avatar) || "",
    }, counts));
  } catch (e) {}
}

// Read with the ETag, so the write can say "only if nobody else wrote since".
async function r2GetTagged(key) {
  try {
    const r = await s3.send(new GetObjectCommand({ Bucket: BUCKET, Key: key }));
    return { data: JSON.parse(await r.Body.transformToString()), etag: r.ETag || null };
  } catch (e) {
    if (e.name === "NoSuchKey" || e.$metadata?.httpStatusCode === 404) return { data: null, etag: null };
    throw e;
  }
}
// Read-modify-write that cannot lose a concurrent write: the PUT carries
// If-Match (or If-None-Match for a new file) and a 412 means another reader
// got there first — re-read and apply the change again. `fn` returns the new
// value, or undefined to write nothing.
async function r2Update(key, fn) {
  for (let attempt = 0; attempt < 6; attempt++) {
    const { data, etag } = await r2GetTagged(key);
    const next = fn(data);
    if (next === undefined) return data;
    const cmd = { Bucket: BUCKET, Key: key, Body: JSON.stringify(next), ContentType: "application/json" };
    if (etag) cmd.IfMatch = etag; else cmd.IfNoneMatch = "*";
    try {
      await s3.send(new PutObjectCommand(cmd));
      return next;
    } catch (e) {
      const clash = e.name === "PreconditionFailed" || e.$metadata?.httpStatusCode === 412;
      if (!clash) throw e;
      await new Promise(function (r) { setTimeout(r, 40 + Math.random() * 120); });
    }
  }
  throw new Error("Too many people writing at once — try again.");
}

function catalogueBook(filename) {
  try {
    const all = JSON.parse(fs.readFileSync(path.join(process.cwd(), "private", "books", "index.json"), "utf8"));
    const b = all.find(function (x) { return x && x.filename === filename; });
    if (!b) return null;
    if (b.restricted) return null;
    if (isPublicSite() && !b.public) return null;
    return b;
  } catch (e) { return null; }
}

// When the group last did something, from the record itself: its creation,
// the newest highlight, note or pen stroke still on the page, and the newest
// line of chat. Worked out rather than stored, so joining, closing or deleting
// a mark never counts as activity, and groups from before this rule sort by
// what actually happened in them.
function groupActivity(g) {
  let t = g.createdAt || 0;
  for (const k of Object.keys(g.items || {})) {
    const it = g.items[k];
    if (it && !it.deleted) t = Math.max(t, it.updatedAt || it.createdAt || 0);
  }
  const chat = Array.isArray(g.chat) ? g.chat : [];
  if (chat.length) t = Math.max(t, chat[chat.length - 1].at || 0);
  return t;
}

// A group can read a file its members bring themselves rather than a book
// from the library. The group then carries what identifies that file — a
// fingerprint of its text — so every member's copy can be checked against
// the one the group was started on, and the recording the starter put beside
// it, which is the one thing about an own book worth sharing.
function cleanOwn(raw) {
  const o = raw && typeof raw === "object" ? raw : null;
  if (!o) return null;
  // Two fingerprints of the same text: a SHA-256 digest, and a plain one the
  // browser can always compute — crypto.subtle is missing outside a secure
  // context, and a reader there was being told their own file was not the
  // group's. Either may be absent; one of them has to be there.
  const hash = /^[a-f0-9]{16,64}$/.test(String(o.hash || "")) ? String(o.hash) : "";
  const fp = /^[a-f0-9]{16,32}$/.test(String(o.fp || "")) ? String(o.fp) : "";
  // The file itself, by its bytes — what two readers with the same download
  // hold in common no matter what either one's parser made of it. This is
  // what a group's file is known by now; the two text fingerprints above stay
  // for groups started before it, and for copies saved by an older build.
  const rawBytes = (o.bytes && typeof o.bytes === "object") ? o.bytes : null;
  const bytes = rawBytes ? {
    sha: /^[a-f0-9]{16,64}$/.test(String(rawBytes.sha || "")) ? String(rawBytes.sha) : "",
    fp: /^[a-f0-9]{16,32}$/.test(String(rawBytes.fp || "")) ? String(rawBytes.fp) : "",
    size: Math.max(0, Math.min(4294967295, Math.round(Number(rawBytes.size) || 0))),
  } : null;
  const hasBytes = !!(bytes && (bytes.sha || bytes.fp));
  if (!hash && !fp && !hasBytes) return null;
  const title = String(o.title || "").trim().slice(0, 120);
  if (!title) return null;
  // The name of the starter's file, kept so the group can say what everyone
  // needs to go and find. The text fingerprint is what actually decides
  // whether two copies are the same book — a file renamed is still the same
  // file — but a reader looking for it needs a name and an extension, and a
  // reader whose copy does not match needs to be told which one does.
  const file = String(o.file || "").trim().replace(/^.*[\\/]/, "").slice(0, 160);
  return {
    hash,
    fp,
    bytes: hasBytes ? bytes : null,
    // The opening words of the copy, and the build that read it — so a
    // reader whose copy does not match can be shown how the two differ
    // instead of being told two hex strings disagree.
    head: String(o.head || "").replace(/\s+/g, " ").trim().slice(0, 120),
    build: String(o.build || "").slice(0, 40),
    title,
    author: String(o.author || "").trim().slice(0, 120),
    file,
    ext: (file.match(/\.([A-Za-z0-9]{1,8})$/) || ["", ""])[1].toLowerCase(),
    words: Math.max(0, Math.min(5000000, Math.round(Number(o.words) || 0))),
    chapters: Math.max(0, Math.min(5000, Math.round(Number(o.chapters) || 0))),
  };
}

const YT_ID = /^[A-Za-z0-9_-]{11}$/;
// A recording can also be a plain audio file rather than a YouTube page, and
// either kind can carry where each chapter begins and ends inside it.
const AUDIO_URL = /^https:\/\/[^\s"'<>]+\.(mp3|m4a|aac|ogg|oga|opus|wav|flac|webm)(\?[^\s"'<>]*)?$/i;
function cleanAudio(raw) {
  const a = raw && typeof raw === "object" ? raw : null;
  if (!a) return null;
  const out = { mode: a.mode === "chapter" ? "chapter" : "book", id: "", url: "", byChapter: {}, bounds: {} };
  if (YT_ID.test(String(a.id || ""))) out.id = String(a.id);
  const url = String(a.url || "").trim();
  if (url.length <= 500 && AUDIO_URL.test(url)) out.url = url;
  const by = a.byChapter && typeof a.byChapter === "object" ? a.byChapter : {};
  for (const k of Object.keys(by).slice(0, 2000)) {
    if (!/^\d{1,4}$/.test(k)) continue;
    if (YT_ID.test(String(by[k] || ""))) out.byChapter[k] = String(by[k]);
  }
  const bd = a.bounds && typeof a.bounds === "object" ? a.bounds : {};
  for (const k of Object.keys(bd).slice(0, 2000)) {
    if (!/^\d{1,4}$/.test(k)) continue;
    const v = bd[k] || {};
    const st = Math.max(0, Math.min(360000, Math.round(Number(v.start) || 0)));
    const en = Math.max(0, Math.min(360000, Math.round(Number(v.end) || 0)));
    if (st || en) out.bounds[k] = { start: st, end: en };
  }
  if (!out.id && !out.url && !Object.keys(out.byChapter).length) return null;
  return out;
}

function groupSummary(g) {
  return {
    id: g.id, name: g.name, filename: g.filename, title: g.title, author: g.author,
    own: g.own || null, audio: g.audio || null,
    ownerName: g.ownerName, createdAt: g.createdAt, lastActive: groupActivity(g),
    closed: !!g.closed,
    members: Object.keys(g.members || {}).length,
    items: Object.keys(g.items || {}).filter(function (k) { return !g.items[k].deleted; }).length,
  };
}

async function refreshIndex(g, remove) {
  await r2Update(`${GROUPS}/index.json`, function (cur) {
    const idx = (cur && Array.isArray(cur.groups)) ? cur.groups : [];
    const rest = idx.filter(function (x) { return x.id !== g.id; });
    if (!remove) rest.unshift(groupSummary(g));
    rest.sort(function (a, b) { return (b.lastActive || 0) - (a.lastActive || 0); });
    return { groups: rest.slice(0, 300), v: (cur && cur.v) || 0 };
  });
}

// Every group a reader has ever been in, so they can always get back to it —
// even one that has dropped off the public list or been closed.
async function rememberMembership(uid, gid) {
  let cur = null;
  try { cur = await r2Get(uid, "groups"); } catch (e) {}
  const ids = (cur && Array.isArray(cur.ids)) ? cur.ids : [];
  if (ids.indexOf(gid) === -1) {
    ids.unshift(gid);
    await r2Put(uid, "groups", { ids: ids.slice(0, 500) });
  }
}

// ── The reading room ─────────────────────────────────────────────────────
//
async function handleGroup(req, res, user, action) {
  let body = req.body;
  if (typeof body === "string") { try { body = JSON.parse(body); } catch { body = {}; } }
  body = body || {};
  const q = req.query || {};
  const account = await findAccount(user.email).catch(function () { return null; });
  const me = {
    uid: user.id,
    name: (account && account.username) || String(user.email || "").split("@")[0],
    avatar: (account && account.avatar) || "",
  };
  const gid = String(body.id || q.id || "");
  const gkey = function (id) { return `${GROUPS}/${id}.json`; };
  const validId = /^[a-z0-9]{8}$/.test(gid);

  // Group reads are for readers with a username: it is what the other
  // members see beside every note and chat line, and an email address cut at
  // the @ is not something anyone chose to show strangers. Only the public
  // list of groups is open without one.
  if (action !== "list" && !(account && account.username)) {
    return res.status(403).json({ error: "Choose a username to take part in group reads.", needUsername: true });
  }

  try {
    // Every group, newest activity first. Public by design: the list is how
    // readers find one another.
    if (action === "list" && req.method === "GET") {
      let idx = (await r2GetTagged(`${GROUPS}/index.json`)).data;
      // Once: the list was kept by a stored time that joining also moved.
      // Re-read every group and re-summarise it by what happened in it.
      if (idx && Array.isArray(idx.groups) && idx.v !== 2) {
        const fresh = [];
        for (const e of idx.groups) {
          const g = (await r2GetTagged(gkey(e.id))).data;
          if (g) fresh.push(groupSummary(g));
        }
        idx = await r2Update(`${GROUPS}/index.json`, function (cur) {
          const byId = {};
          fresh.forEach(function (x) { byId[x.id] = x; });
          const list = ((cur && cur.groups) || []).map(function (x) { return byId[x.id] || x; });
          return { groups: list, v: 2 };
        });
      }
      const groups = ((idx && idx.groups) || []).filter(function (g) {
        return !isPublicSite() || !!g.own || !!catalogueBook(g.filename);
      }).sort(function (a, b) { return (b.lastActive || 0) - (a.lastActive || 0); });
      return res.status(200).json({ groups });
    }

    if (action === "mine" && req.method === "GET") {
      let cur = null;
      try { cur = await r2Get(me.uid, "groups"); } catch (e) {}
      const ids = (cur && Array.isArray(cur.ids)) ? cur.ids : [];
      const out = [];
      for (const id of ids.slice(0, 100)) {
        if (!/^[a-z0-9]{8}$/.test(id)) continue;
        const g = (await r2GetTagged(gkey(id))).data;
        if (g && !g.deleted && g.members && g.members[me.uid]) out.push(groupSummary(g));
      }
      out.sort(function (a, b) { return (b.lastActive || 0) - (a.lastActive || 0); });
      return res.status(200).json({ groups: out });
    }

    if (action === "create" && req.method === "POST") {
      const name = String(body.name || "").trim().replace(/\s+/g, " ");
      if (name.length < 3 || name.length > 60) return res.status(400).json({ error: "Give the group a name of 3 to 60 characters." });
      const own = cleanOwn(body.own);
      const book = own ? null : catalogueBook(String(body.filename || ""));
      if (!own && !book) {
        return res.status(400).json({ error: "Choose a book from the library, or one of your own files." });
      }
      const idx = (await r2GetTagged(`${GROUPS}/index.json`)).data;
      const mine = ((idx && idx.groups) || []).filter(function (g) { return g.ownerName === me.name; });
      if (mine.length >= 5) return res.status(400).json({ error: "You already run five group reads — end one first." });
      const id = Array.from({ length: 8 }, function () {
        return "abcdefghjkmnpqrstuvwxyz23456789"[Math.floor(Math.random() * 31)];
      }).join("");
      const now = Date.now();
      const g = {
        id, name,
        filename: book ? book.filename : "",
        own: own || null,
        title: book ? (book.title || "") : own.title,
        author: book ? (book.author || "") : own.author,
        owner: me.uid, ownerName: me.name, createdAt: now, lastActive: now,
        members: { [me.uid]: { name: me.name, avatar: me.avatar, joinedAt: now, seenAt: now } },
        items: {},
      };
      await r2Update(gkey(id), function (cur) { return cur ? undefined : g; });
      await refreshIndex(g);
      await rememberMembership(me.uid, id);
      return res.status(200).json({ ok: true, group: groupSummary(g) });
    }

    if (!validId) return res.status(400).json({ error: "No such group." });

    if (action === "join" && req.method === "POST") {
      const now = Date.now();
      const g = await r2Update(gkey(gid), function (cur) {
        if (!cur || cur.deleted) return undefined;
        cur.members = cur.members || {};
        cur.members[me.uid] = Object.assign({}, cur.members[me.uid] || { joinedAt: now },
          { name: me.name, avatar: me.avatar, seenAt: now });
        return cur;
      });
      if (!g || g.deleted) return res.status(404).json({ error: "No such group." });
      await refreshIndex(g);
      await rememberMembership(me.uid, gid);
      return res.status(200).json({ ok: true, group: groupSummary(g) });
    }

    // Leaving, for real: out of the members, off your own list of groups. It
    // was a no-op before — the page simply stopped showing the group and the
    // membership stayed for good, so a reader who had finished with a group
    // had no way to be rid of it. What they wrote in the group stays in the
    // group: the others are reading around it, and a note vanishing from
    // under someone else's reply helps nobody. Joining again is a click.
    //
    // The starter cannot leave their own group — with the owner gone nobody
    // could ever change or close it. They delete it instead.
    if (action === "leave" && req.method === "POST") {
      const cur = (await r2GetTagged(gkey(gid))).data;
      if (cur && !cur.deleted && cur.owner === me.uid && !user.isAdmin) {
        return res.status(400).json({
          error: "You started this group — leaving would leave it with nobody to run it. Delete it instead.",
        });
      }
      const g = await r2Update(gkey(gid), function (c) {
        if (!c || c.deleted) return undefined;
        if (!c.members || !c.members[me.uid]) return undefined;
        delete c.members[me.uid];
        return c;
      });
      try {
        const mine = await r2Get(me.uid, "groups");
        const ids = (mine && Array.isArray(mine.ids)) ? mine.ids : [];
        if (ids.indexOf(gid) !== -1) {
          await r2Put(me.uid, "groups", { ids: ids.filter(function (x) { return x !== gid; }) });
        }
      } catch (e) { /* the group is left either way */ }
      if (g) await refreshIndex(g);
      return res.status(200).json({ ok: true, left: gid });
    }

    // The starter can re-point the group at the copy of the file they have
    // open. Two copies of the same novel are not always the same text — an
    // EPUB and an FB2 differ, and so do two FB2s from two libraries — and the
    // fingerprint turns anything that is not the group's exact file away.
    // When it is the starter whose copy no longer matches, this is how they
    // say "this one is the group's", rather than starting over.
    if (action === "own" && req.method === "POST") {
      const cur = (await r2GetTagged(gkey(gid))).data;
      if (!cur || cur.deleted) return res.status(404).json({ error: "No such group." });
      if (cur.owner !== me.uid && !user.isAdmin) {
        return res.status(403).json({ error: "Only the reader who started it can change its file." });
      }
      if (!cur.own) return res.status(400).json({ error: "This group reads a book from the library." });
      const own = cleanOwn(body.own);
      if (!own) return res.status(400).json({ error: "That file could not be read." });
      const g = await r2Update(gkey(gid), function (c) {
        if (!c || c.deleted) return undefined;
        c.own = own;
        c.title = own.title || c.title;
        c.author = own.author || c.author;
        c.ownChangedAt = Date.now();
        return c;
      });
      if (g) await refreshIndex(g);
      return res.status(200).json({ ok: true, group: groupSummary(g) });
    }

    // The starter can delete a group they started. Unlike closing, this does
    // take everything with it — the chat, and every highlight and note made
    // in the group. What each member marked while reading alone is elsewhere
    // and untouched. The file is replaced by a tombstone rather than removed,
    // so a poll already in flight gets "no such group" instead of writing the
    // group back into existence.
    if (action === "delete" && req.method === "POST") {
      const cur = (await r2GetTagged(gkey(gid))).data;
      if (!cur || cur.deleted) return res.status(404).json({ error: "No such group." });
      if (cur.owner !== me.uid && !user.isAdmin) {
        return res.status(403).json({ error: "Only the reader who started it can delete it." });
      }
      await r2Update(gkey(gid), function (c) {
        if (!c || c.deleted) return undefined;
        return { id: c.id, deleted: true, deletedAt: Date.now(), ownerName: c.ownerName || "" };
      });
      await refreshIndex({ id: gid }, true);
      return res.status(200).json({ ok: true, deleted: gid });
    }

    // The starter can close a group to new marks. Nothing is removed: every
    // member keeps reading what is there, forever.
    if ((action === "close" || action === "end") && req.method === "POST") {
      const cur = (await r2GetTagged(gkey(gid))).data;
      if (!cur || cur.deleted) return res.status(404).json({ error: "No such group." });
      if (cur.owner !== me.uid && !user.isAdmin) return res.status(403).json({ error: "Only the reader who started it can close it." });
      const g = await r2Update(gkey(gid), function (c) {
        if (!c) return undefined;
        c.closed = true; c.closedAt = Date.now();
        return c;
      });
      if (g) await refreshIndex(g);
      return res.status(200).json({ ok: true });
    }

    // The poll. Everything that changed since the reader last asked, plus who
    // is here. `now` is the server's clock, which the client echoes back as
    // `since`, so no two machines' clocks ever have to agree.
    if (action === "items" && req.method === "GET") {
      const { data: g } = await r2GetTagged(gkey(gid));
      if (!g || g.deleted) return res.status(404).json({ error: "No such group." });
      if (!g.members || !g.members[me.uid]) return res.status(403).json({ error: "Join the group first." });
      const since = Number(q.since) || 0;
      const items = [];
      for (const k of Object.keys(g.items || {})) {
        const it = g.items[k];
        if ((it.updatedAt || 0) > since) items.push(it);
      }
      const now = Date.now();
      // Presence: who has polled in the last half-minute counts as here.
      const members = Object.keys(g.members).map(function (uid) {
        const m = g.members[uid];
        return { name: m.name, avatar: m.avatar, here: now - (m.seenAt || 0) < 30000, owner: uid === g.owner };
      });
      // Marking this reader seen costs a write, so it happens at most every
      // twenty seconds rather than on every poll.
      if (now - ((g.members[me.uid] || {}).seenAt || 0) > 20000) {
        r2Update(gkey(gid), function (cur) {
          if (!cur || !cur.members || !cur.members[me.uid]) return undefined;
          cur.members[me.uid].seenAt = now;
          return cur;
        }).catch(function () {});
      }
      // The group's chat rides the same poll: the messages newer than
      // `since`, from the same file the notes are in, so talking costs no
      // extra request every three seconds.
      const allChat = Array.isArray(g.chat) ? g.chat : [];
      const chat = allChat.filter(function (m) { return !m.del && (m.at || 0) > since; });
      const removed = allChat.filter(function (m) { return m.del && m.del > since; })
        .map(function (m) { return m.id; });
      return res.status(200).json({ now, items, chat, removed, members, group: groupSummary(g), isOwner: g.owner === me.uid });
    }

    // The recording the starter has put beside the group's own file. One
    // YouTube link for the whole book, or one per chapter, exactly as the
    // reader's own-book page stores it — so a member who has the same file
    // hears the same recording without pasting anything.
    if (action === "audio" && req.method === "POST") {
      const audio = cleanAudio(body.audio);
      let refused = "";
      const g = await r2Update(gkey(gid), function (cur) {
        if (!cur || cur.deleted) { refused = "No such group."; return undefined; }
        if (cur.owner !== me.uid) { refused = "Only the reader who started the group can set its recording."; return undefined; }
        if (!cur.own) { refused = "That group reads a book from the library, which brings its own recording."; return undefined; }
        cur.audio = audio;
        return cur;
      });
      if (refused) return res.status(400).json({ error: refused });
      if (!g || g.deleted) return res.status(404).json({ error: "No such group." });
      return res.status(200).json({ ok: true, audio: g.audio || null });
    }

    // A line in the group's chat. Kept in the group file with everything
    // else, newest last, the oldest dropping off past GROUP_CHAT_CAP. Plain
    // text only — the client draws it as text, never as markup.
    if (action === "say" && req.method === "POST") {
      const text = String(body.text || "").replace(/\r\n?/g, "\n").replace(/[\u0000-\u0008\u000b-\u001f]/g, "").trim();
      if (!text) return res.status(400).json({ error: "Nothing to send." });
      if (text.length > 1000) return res.status(400).json({ error: "Keep a message under 1000 characters." });
      const now = Date.now();
      let refused = "", msg = null;
      const g = await r2Update(gkey(gid), function (cur) {
        if (!cur || cur.deleted) { refused = "No such group."; return undefined; }
        if (cur.closed || cur.ended) { refused = "This group read is closed — its chat stays, but it takes no new messages."; return undefined; }
        if (!cur.members || !cur.members[me.uid]) { refused = "Join the group first."; return undefined; }
        const chat = Array.isArray(cur.chat) ? cur.chat : [];
        const last = chat.filter(function (m) { return m.uid === me.uid; }).pop();
        if (last && now - last.at < 800) { refused = "One moment — that was fast."; return undefined; }
        msg = {
          id: now.toString(36) + Math.random().toString(36).slice(2, 6),
          uid: me.uid, name: me.name, avatar: me.avatar, text, at: now,
        };
        chat.push(msg);
        cur.chat = chat.slice(-GROUP_CHAT_CAP);
        cur.lastActive = now;
        cur.members[me.uid].seenAt = now;
        return cur;
      });
      if (refused) return res.status(400).json({ error: refused });
      try { await refreshIndex(g); } catch (e) {}
      return res.status(200).json({ ok: true, msg });
    }

    // A line out of the group's chat: its writer, the group's starter, or
    // the site's admin. The group's record is the members' own, so nobody
    // else can edit it.
    if (action === "unsay" && req.method === "POST") {
      const id = String(body.msg || "");
      let refused = "";
      await r2Update(gkey(gid), function (cur) {
        if (!cur || cur.deleted) { refused = "No such group."; return undefined; }
        if (!cur.members || !cur.members[me.uid]) { refused = "Join the group first."; return undefined; }
        const chat = Array.isArray(cur.chat) ? cur.chat : [];
        const m = chat.find(function (x) { return x.id === id; });
        if (!m) { refused = "That message is already gone."; return undefined; }
        if (m.uid !== me.uid && cur.owner !== me.uid && !user.isAdmin) {
          refused = "That message is not yours."; return undefined;
        }
        m.del = Date.now(); m.text = "";
        cur.chat = chat;
        return cur;
      });
      if (refused) return res.status(400).json({ error: refused });
      return res.status(200).json({ ok: true, id });
    }

    if (action === "put" && req.method === "POST") {
      const it = cleanAnnot(body.item);
      if (!it) return res.status(400).json({ error: "That annotation could not be read." });
      const now = Date.now();
      let refused = "";
      const g = await r2Update(gkey(gid), function (cur) {
        if (!cur || cur.deleted) { refused = "No such group."; return undefined; }
        if (cur.closed || cur.ended) { refused = "This group read is closed — its notes stay, but it takes no new ones."; return undefined; }
        if (!cur.members || !cur.members[me.uid]) { refused = "Join the group first."; return undefined; }
        cur.items = cur.items || {};
        const prev = cur.items[it.id];
        // Only the reader who made an annotation may change or remove it. Not
        // even the starter can take away another member's note: the group's
        // pages are everyone's record.
        if (prev && prev.by && prev.by.uid !== me.uid) {
          refused = "That note belongs to another reader."; return undefined;
        }
        if (!prev && Object.keys(cur.items).length >= GROUP_ITEM_CAP) { refused = "This group's page is full."; return undefined; }
        const bookKeyOk = cur.own ? true : (!it.bookKey || it.bookKey.indexOf(cur.filename) === 0);
        if (!bookKeyOk) { refused = "That annotation is for another book."; return undefined; }
        it.updatedAt = now;
        it.by = prev && prev.by ? prev.by : { uid: me.uid, name: me.name, avatar: me.avatar };
        cur.items[it.id] = it;
        cur.lastActive = now;
        return cur;
      });
      if (refused) return res.status(400).json({ error: refused });
      if (!g || g.deleted) return res.status(404).json({ error: "No such group." });
      // The public list only needs to move when the count does.
      try { await refreshIndex(g); } catch (e) {}
      return res.status(200).json({ ok: true, item: g.items[it.id] });
    }

    return res.status(404).json({ error: "Unknown group action: " + action });
  } catch (err) {
    return res.status(500).json({ error: err.message || "Group read failed." });
  }
}

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
