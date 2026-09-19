// Lists the site's accounts and approves or revokes them. Admin only.
//
// Accounts live in R2 (see lib/auth.js) rather than in a third-party user
// directory, so this reads the account index and returns one row each.
// New accounts start unapproved and cannot sign in until approved here;
// accounts that predate the approval flow have no `approved` field and are
// treated as approved, so existing readers keep working untouched.
import fs from "node:fs";
import path from "node:path";
import { requireAdmin } from "./helpers.js";
import { listAccounts, setApproval, isAdminEmail, findAccount, userIdFor, r2GetJson,
         r2PutJson, userDataKey, readDaily, todayKey } from "../auth.js";

// The daily reading log, summed. Deliberately a copy of what src/stats.js
// does on the client rather than an import of it: that module is bundled for
// the browser and this runs in a serverless function, and the arithmetic is
// six lines. A day counts as active when anything at all was recorded on it —
// a lower bar than the streak's, because the question here is "were they here"
// rather than "did they hit the goal".
//
// The streak uses the app's own default goals (500 words or 10 cards). A
// reader who has set their own goals will see a streak here computed against
// the defaults; the panel says which, rather than quietly showing a figure
// that does not match the one on their own page.
function logTotals(stats) {
  const s = (stats && typeof stats === "object" && !Array.isArray(stats)) ? stats : {};
  const keys = Object.keys(s).filter(function (k) { return /^\d{4}-\d{2}-\d{2}$/.test(k); }).sort();
  let read = 0, practiced = 0, days = 0, last = null;
  for (const k of keys) {
    const r = s[k] || {};
    read += Number(r.read) || 0;
    practiced += Number(r.practiced) || 0;
    if ((Number(r.read) || 0) > 0 || (Number(r.practiced) || 0) > 0) { days++; last = k; }
  }
  // Consecutive met days ending today or yesterday — today is not lost until
  // midnight, so an unfinished today does not break the run.
  const met = {};
  for (const k of keys) met[k] = ((Number((s[k] || {}).read) || 0) >= 500) ||
                                 ((Number((s[k] || {}).practiced) || 0) >= 10);
  const shift = function (key, n) {
    const d = new Date(key + "T12:00:00Z");
    d.setUTCDate(d.getUTCDate() + n);
    return d.toISOString().slice(0, 10);
  };
  let cursor = new Date().toISOString().slice(0, 10);
  if (!met[cursor]) cursor = shift(cursor, -1);
  let streak = 0;
  while (met[cursor]) { streak++; cursor = shift(cursor, -1); }
  const recent = keys.slice(-56).map(function (k) {
    const r = s[k] || {};
    return { date: k, read: Number(r.read) || 0, practiced: Number(r.practiced) || 0 };
  });
  return { read, practiced, days, last, streak, recent };
}

// Everything the site knows about one reader, gathered for the admin panel.
// Reads the same per-user R2 files the app itself writes (vocab, tips,
// progress, finished, settings) plus the account record, and returns totals
// with enough detail for the panel's drill-down windows — but never the
// password hash, which has no business leaving the bucket.
async function userDetail(email) {
  const account = await findAccount(email);
  if (!account) return null;
  const uid = account.id || userIdFor(email);
  const [vocab, tips, progress, finished, settings, stats, learned, songs, drills] = await Promise.all([
    r2GetJson(userDataKey(uid, "vocab")),
    r2GetJson(userDataKey(uid, "tips")),
    r2GetJson(userDataKey(uid, "progress")),
    r2GetJson(userDataKey(uid, "finished")),
    r2GetJson(userDataKey(uid, "settings")),
    r2GetJson(userDataKey(uid, "stats")),
    r2GetJson(userDataKey(uid, "learned")),
    r2GetJson(userDataKey(uid, "songs")),
    r2GetJson(userDataKey(uid, "drills")),
  ]);
  const prog = (progress && typeof progress === "object" && !Array.isArray(progress)) ? progress : {};
  const fin  = (finished && typeof finished === "object" && !Array.isArray(finished)) ? finished : {};
  // One row per book the reader has opened, newest first. cidx/totalChapters
  // give the panel a position; lastRead orders the list.
  const reading = Object.keys(prog).map(function (k) {
    const p = prog[k] || {};
    return {
      key: k,
      title: p.title || k,
      author: p.author || "",
      cidx: p.cidx || 0,
      pidx: p.pidx || 0,
      totalChapters: p.totalChapters || 0,
      lastRead: p.lastRead || 0,
    };
  }).sort(function (a, b) { return (b.lastRead || 0) - (a.lastRead || 0); });
  // Unmarked books stay in the map as tombstones ({removed:true}) so the
  // unmark can win cross-device merges — they are not finished books.
  const finishedList = Object.keys(fin).filter(function (k) {
    return fin[k] && !fin[k].removed;
  }).map(function (k) {
    const f = fin[k] || {};
    return { key: k, title: f.title || k, author: f.author || "", at: f.at || 0 };
  }).sort(function (a, b) { return (b.at || 0) - (a.at || 0); });
  const vocabList = Array.isArray(vocab) ? vocab : [];
  const learnedList = Array.isArray(learned) ? learned : [];
  const log = logTotals(stats);
  const dr = (drills && typeof drills === "object" && !Array.isArray(drills)) ? drills : {};
  // Songs from the Music tab, most recently opened first. `n` is how many
  // times that song was opened, so the list doubles as what they keep
  // returning to rather than merely what they once clicked.
  const songMap = (songs && typeof songs === "object" && !Array.isArray(songs)) ? songs : {};
  const songList = Object.keys(songMap).map(function (k) {
    const v = songMap[k] || {};
    return { id: k, title: v.title || k, artist: v.artist || "", n: v.n || 1, at: v.at || 0 };
  }).sort(function (a, b) { return (b.at || 0) - (a.at || 0); });
  // Which books they drilled, so "forty questions" can be asked of where.
  const drillBooks = Object.keys(dr.byBook || {}).map(function (k) {
    const v = dr.byBook[k] || {};
    return { key: k, title: v.title || k, runs: v.runs || 0,
             questions: v.questions || 0, correct: v.correct || 0 };
  }).sort(function (a, b) { return (b.questions || 0) - (a.questions || 0); });
  return {
    email: account.email,
    id: uid,
    createdAt: account.createdAt || null,
    lastLoginAt: account.lastLoginAt || null,
    lastSeenAt: account.lastSeenAt || null,
    loginCount: account.loginCount || 0,
    approvedAt: account.approvedAt || null,
    passwordChangedAt: account.passwordChangedAt || null,
    isAdmin: isAdminEmail(account.email),
    counts: {
      vocab: vocabList.length,
      tips: Array.isArray(tips) ? tips.length : 0,
      booksOpened: reading.length,
      booksFinished: finishedList.length,
      hasSettings: !!settings,
      // The daily log behind the streak dots: Russian words scrolled through
      // in the reader, vocabulary-quiz answers, and days on which either
      // happened at all.
      wordsRead: log.read,
      practiced: log.practiced,
      daysActive: log.days,
      lastActive: log.last,
      streak: log.streak,
      learned: learnedList.length,
      songs: songList.length,
      songPlays: songList.reduce(function (n, x) { return n + (x.n || 0); }, 0),
      drillRuns: dr.runs || 0,
      drillQuestions: dr.questions || 0,
      drillCorrect: dr.correct || 0,
    },
    // A zero means two very different things and the panel must not conflate
    // them. Vocabulary, tips and marked-read have been written to R2 since the
    // beginning, so zero there is a real zero. Reading progress was never sent
    // to the server until now, so a missing file means "never measured" — and
    // the login counter did not exist at all, though lastLoginAt did, so an
    // account with a last-visit date and no count has certainly signed in.
    recorded: {
      progress: progress !== null,
      finished: finished !== null,
      vocab: vocab !== null,
      tips: tips !== null,
      settings: settings !== null,
      stats: stats !== null,
      learned: learned !== null,
      // Songs and case drills were kept in the browser until September 2026,
      // so a missing file here means the site never asked, not that the reader
      // never opened a song or finished a drill.
      songs: songs !== null,
      drills: drills !== null,
      logins: (account.loginCount || 0) > 0 || !account.lastLoginAt,
    },
    // Where the panel looked. Without this, an empty reader is ambiguous: no
    // data, or data filed under another id? Govorim predates the current auth,
    // and accounts carried over from the Clerk setup have their files under a
    // user_2… id that no longer derives from the email — see
    // /api/admin/import-userdata, which exists for exactly that. Showing the
    // id and which files answered turns the question into a fact.
    storage: { prefix: userDataKey(uid, "*").replace(/\*\.json$/, "") },
    reading: reading.slice(0, 100),
    finished: finishedList.slice(0, 100),
    songs: songList.slice(0, 200),
    drillBooks: drillBooks.slice(0, 100),
    // The last eight weeks of the daily log, for the little strip in the
    // window — the same shape the site trend uses.
    days: log.recent,
    // The words themselves, newest last as the app appends them. Capped: the
    // panel shows a scrollable window, not the whole dictionary in one JSON.
    vocab: vocabList.slice(-500).map(function (v) {
      if (typeof v === "string") return { ru: v, en: "" };
      return { ru: v.ru || "", en: v.en || "", addedAt: v.addedAt || 0 };
    }),
  };
}

// Site-wide totals, summed across every account plus whatever the anonymous
// counter has seen. Accounts are read one at a time — the R2 token is
// object-scoped and cannot list a bucket, so there is no bulk read to be had —
// which is fine at this library's scale and would want caching at a thousand.
async function siteTotals() {
  const accounts = await listAccounts();
  const t = { accounts: accounts.length, booksOpened: 0, vocab: 0, finished: 0, tips: 0,
              readersWithProgress: 0, wordsRead: 0, practiced: 0, daysActive: 0,
              learned: 0, songs: 0, songPlays: 0, drillRuns: 0, drillQuestions: 0,
              drillCorrect: 0, readersWithDrills: 0, readersWithSongs: 0 };
  for (const a of accounts) {
    const uid = a.id || userIdFor(a.email);
    const [vocab, tips, progress, finished, stats, learned, songs, drills] = await Promise.all([
      r2GetJson(userDataKey(uid, "vocab")),
      r2GetJson(userDataKey(uid, "tips")),
      r2GetJson(userDataKey(uid, "progress")),
      r2GetJson(userDataKey(uid, "finished")),
      r2GetJson(userDataKey(uid, "stats")),
      r2GetJson(userDataKey(uid, "learned")),
      r2GetJson(userDataKey(uid, "songs")),
      r2GetJson(userDataKey(uid, "drills")),
    ]);
    const lg = logTotals(stats);
    t.wordsRead += lg.read;
    t.practiced += lg.practiced;
    t.daysActive += lg.days;
    if (Array.isArray(learned)) t.learned += learned.length;
    if (songs && typeof songs === "object") {
      const ks = Object.keys(songs);
      if (ks.length) t.readersWithSongs += 1;
      t.songs += ks.length;
      for (const k of ks) t.songPlays += Number((songs[k] || {}).n) || 0;
    }
    if (drills && typeof drills === "object") {
      if (drills.runs) t.readersWithDrills += 1;
      t.drillRuns += Number(drills.runs) || 0;
      t.drillQuestions += Number(drills.questions) || 0;
      t.drillCorrect += Number(drills.correct) || 0;
    }
    if (Array.isArray(vocab)) t.vocab += vocab.length;
    if (Array.isArray(tips))  t.tips  += tips.length;
    if (progress && typeof progress === "object") {
      const n = Object.keys(progress).length;
      t.booksOpened += n;
      if (n) t.readersWithProgress += 1;
    }
    if (finished && typeof finished === "object") t.finished += Object.keys(finished).filter(function (k) { return finished[k] && !finished[k].removed; }).length;
  }
  // Signed-out readers keep everything in their own browser, so the only thing
  // the server can know about them is a count it was told about. See the
  // ?anon= branch in api/user-data.js.
  const anon = await r2GetJson(userDataKey("_stats", "anon"));
  t.anonBooksOpened = (anon && anon.booksOpened) || 0;
  t.anonSince = (anon && anon.since) || null;
  t.totalBooksOpened = t.booksOpened + t.anonBooksOpened;
  // Today, from the per-day tallies. Dates are UTC so the day does not shift
  // under whoever is reading the panel.
  const daily = await readDaily();
  const k = todayKey();
  const d0 = daily[k] || {};
  t.today = {
    date: k,
    opens: d0.opens || 0,
    anonOpens: d0.anonOpens || 0,
    accountOpens: Math.max(0, (d0.opens || 0) - (d0.anonOpens || 0)),
    logins: d0.logins || 0,
    visits: d0.visits || 0,
    counting: Object.keys(daily).length > 0,
  };
  const site = await r2GetJson(userDataKey("_stats", "site"));
  t.visits = (site && site.visits) || 0;
  t.visitsSince = (site && site.since) || null;
  // Presses on the two donate buttons. A press is intent, not money: neither
  // PayPal nor Memorial reports back what happened after the reader left, so
  // these say how many people set out to give, never how many did.
  const clicks = await r2GetJson(userDataKey("_stats", "donate-clicks"));
  t.donate = {
    memorial: (clicks && clicks.memorial) || 0,
    costs: (clicks && clicks.costs) || 0,
    since: (clicks && clicks.since) || null,
  };
  t.today.donateMemorial = d0.donateMemorial || 0;
  t.today.donateCosts = d0.donateCosts || 0;
  t.today.songOpens = d0.songOpens || 0;
  // The last fortnight, for the little trend strip.
  t.recent = Object.keys(daily).sort().slice(-14).map(function (day) {
    const v = daily[day] || {};
    return { date: day, visits: v.visits || 0, opens: v.opens || 0, logins: v.logins || 0,
             donateMemorial: v.donateMemorial || 0, donateCosts: v.donateCosts || 0 };
  });
  return t;
}

// How many times each book has been opened, and how many accounts currently
// hold a saved position in it. The first is an event tally written when a book
// opens; the second is derived from the progress files and answers a different
// question — "how many readers are in the middle of this" rather than "how
// often has it been picked up". Both are useful and they are not the same, so
// the panel shows both rather than passing one off as the other.
// Opens recorded before the key filter was fixed had every Cyrillic letter
// stripped out of the filename, so «novel/<Cyrillic title>.fb2» was stored as
// «novel/ - .fb2» and several books shared one nonsense row. Where exactly one
// title in the catalogue collapses to such a key, its count belongs to that
// title and is moved there — and the repaired map is written back, so the row
// is gone for good rather than re-derived on every load. Where more than one
// title collapses to the same key the count cannot be attributed to either, so
// it is dropped: a row nobody can act on is worse than no row.
const OLD_FILTER = /[^\w.\/\- ]+/g;
async function repairLegacyBookKeys(opens) {
  const keys = Object.keys(opens);
  const damaged = keys.filter(function (k) {
    return k && !/[\u0400-\u04FF]/.test(k) && /(^|[\/\-])\s{1,}([\-.]|$)/.test(k);
  });
  if (!damaged.length) return { opens: opens, changed: false };
  let manifest = [];
  try {
    manifest = JSON.parse(fs.readFileSync(path.join(process.cwd(), "private", "books", "index.json"), "utf8"));
  } catch (e) { return { opens: opens, changed: false }; }
  const collapsed = {};
  for (const b of manifest) {
    const fn = (b && b.filename) || "";
    if (!/[\u0400-\u04FF]/.test(fn)) continue;
    const k = fn.replace(OLD_FILTER, "").slice(0, 160);
    (collapsed[k] = collapsed[k] || []).push(fn);
  }
  const next = Object.assign({}, opens);
  let changed = false;
  for (const k of damaged) {
    const owners = collapsed[k];
    if (owners && owners.length === 1) next[owners[0]] = (next[owners[0]] || 0) + next[k];
    delete next[k];
    changed = true;
  }
  return { opens: next, changed: changed };
}

async function bookStats() {
  let opens = (await r2GetJson(userDataKey("_stats", "books"))) || {};
  const repaired = await repairLegacyBookKeys(opens);
  if (repaired.changed) {
    opens = repaired.opens;
    try { await r2PutJson(userDataKey("_stats", "books"), opens); } catch (e) { /* display still works */ }
  }
  const readers = {};
  const accounts = await listAccounts();
  for (const a of accounts) {
    const uid = a.id || userIdFor(a.email);
    const progress = await r2GetJson(userDataKey(uid, "progress"));
    if (!progress || typeof progress !== "object") continue;
    for (const k of Object.keys(progress)) {
      const p = progress[k] || {};
      // Progress is keyed by the reader's own book key; the filename is the
      // stable thing both sides share.
      const id = p.filename || k;
      if (!readers[id]) readers[id] = { readers: 0, title: p.title || "", author: p.author || "" };
      readers[id].readers += 1;
    }
  }
  // The music, counted the same way and returned beside the books: the panel
  // asks one question — what does the library get opened for — and songs are
  // half the answer on a site that ships twenty-two of them.
  const songs = (await r2GetJson(userDataKey("_stats", "songs"))) || {};
  return { opens, readers, songs,
           since: (await r2GetJson(userDataKey("_stats", "anon")) || {}).since || null };
}

// The funding figures the public progress bar reads. Kept here rather than in
// a route of its own because Vercel's function budget is the reason the whole
// admin lives behind one dispatcher.
async function readFunding() {
  return (await r2GetJson(userDataKey("_stats", "funding"))) || { goal: 0, raised: 0, period: "", note: "" };
}

export async function handleUsers(req, res) {
  const a = await requireAdmin(req, res);
  if (!a) return;

  if (req.method === "GET") {
    // /api/admin/users?totals=1 — the whole site at once.
    if (req.query && req.query.totals) {
      try {
        return res.status(200).json({ totals: await siteTotals() });
      } catch (err) {
        return res.status(500).json({ error: "Failed to total: " + (err.message || err) });
      }
    }
    // /api/admin/users?funding=1 — the cost target and what has come in.
    if (req.query && req.query.funding) {
      try { return res.status(200).json({ funding: await readFunding() }); }
      catch (err) { return res.status(500).json({ error: "Failed to read funding: " + (err.message || err) }); }
    }
    // /api/admin/users?books=1 — the per-book tallies.
    if (req.query && req.query.books) {
      try {
        return res.status(200).json(await bookStats());
      } catch (err) {
        return res.status(500).json({ error: "Failed to read book stats: " + (err.message || err) });
      }
    }
    // /api/admin/users?email=… — one reader in full.
    const email = req.query && req.query.email;
    if (email) {
      try {
        const detail = await userDetail(String(email).trim().toLowerCase());
        if (!detail) return res.status(404).json({ error: "No account with that email." });
        return res.status(200).json({ user: detail });
      } catch (err) {
        return res.status(500).json({ error: "Failed to load user: " + (err.message || err) });
      }
    }
    try {
      const users = await listAccounts();
      return res.status(200).json({ users });
    } catch (err) {
      return res.status(500).json({ error: "Failed to list users: " + (err.message || err) });
    }
  }

  if (req.method === "POST" && req.query && req.query.funding) {
    let body = req.body;
    if (typeof body === "string") { try { body = JSON.parse(body); } catch (_) { body = {}; } }
    body = body || {};
    const f = {
      goal: Math.max(0, Number(body.goal) || 0),
      raised: Math.max(0, Number(body.raised) || 0),
      period: String(body.period || "").slice(0, 60),
      note: String(body.note || "").slice(0, 200),
      updatedAt: Date.now(),
    };
    try {
      await r2PutJson(userDataKey("_stats", "funding"), f);
      return res.status(200).json({ ok: true, funding: f });
    } catch (err) {
      return res.status(500).json({ error: "Failed to save funding: " + (err.message || err) });
    }
  }

  if (req.method === "POST") {
    let body = req.body;
    if (typeof body === "string") { try { body = JSON.parse(body); } catch (_) { body = {}; } }
    body = body || {};
    const email = String(body.email || "").trim().toLowerCase();
    if (!email) return res.status(400).json({ error: "email is required" });
    if (isAdminEmail(email)) {
      return res.status(400).json({ error: "The admin account cannot be changed here." });
    }
    const approved = body.approved !== false;
    try {
      const { error } = await setApproval(email, approved);
      if (error) return res.status(404).json({ error });
      const users = await listAccounts();
      return res.status(200).json({ ok: true, users });
    } catch (err) {
      return res.status(500).json({ error: "Failed to update user: " + (err.message || err) });
    }
  }

  return res.status(405).json({ error: "Method not allowed" });
}
