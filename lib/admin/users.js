// Lists the site's accounts and approves or revokes them. Admin only.
//
// Accounts live in R2 (see lib/auth.js) rather than in a third-party user
// directory, so this reads the account index and returns one row each.
// New accounts start unapproved and cannot sign in until approved here;
// accounts that predate the approval flow have no `approved` field and are
// treated as approved, so existing readers keep working untouched.
import { requireAdmin } from "./helpers.js";
import { listAccounts, setApproval, isAdminEmail, findAccount, userIdFor, r2GetJson, userDataKey } from "../auth.js";

// Everything the site knows about one reader, gathered for the admin panel.
// Reads the same per-user R2 files the app itself writes (vocab, tips,
// progress, finished, settings) plus the account record, and returns totals
// with enough detail for the panel's drill-down windows — but never the
// password hash, which has no business leaving the bucket.
async function userDetail(email) {
  const account = await findAccount(email);
  if (!account) return null;
  const uid = account.id || userIdFor(email);
  const [vocab, tips, progress, finished, settings] = await Promise.all([
    r2GetJson(userDataKey(uid, "vocab")),
    r2GetJson(userDataKey(uid, "tips")),
    r2GetJson(userDataKey(uid, "progress")),
    r2GetJson(userDataKey(uid, "finished")),
    r2GetJson(userDataKey(uid, "settings")),
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
  const finishedList = Object.keys(fin).map(function (k) {
    const f = fin[k] || {};
    return { key: k, title: f.title || k, author: f.author || "", at: f.at || 0 };
  }).sort(function (a, b) { return (b.at || 0) - (a.at || 0); });
  const vocabList = Array.isArray(vocab) ? vocab : [];
  return {
    email: account.email,
    id: uid,
    createdAt: account.createdAt || null,
    lastLoginAt: account.lastLoginAt || null,
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
    // The words themselves, newest last as the app appends them. Capped: the
    // panel shows a scrollable window, not the whole dictionary in one JSON.
    vocab: vocabList.slice(-500).map(function (v) {
      if (typeof v === "string") return { ru: v, en: "" };
      return { ru: v.ru || "", en: v.en || "", addedAt: v.addedAt || 0 };
    }),
  };
}

export async function handleUsers(req, res) {
  const a = await requireAdmin(req, res);
  if (!a) return;

  if (req.method === "GET") {
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
