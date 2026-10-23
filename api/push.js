// Push reminders for the daily goals.
//
// A reader who has put the site on their home screen (or any browser with
// Web Push) can have their goals brought to them twice a day, at times they
// set on the My page — eight in the morning and five in the afternoon unless
// they change them — even with the site closed. The browser's subscription is
// kept with the account, one per device, with the device's time zone; a
// scheduler calls ?action=remind every ten minutes — an outside one
// (cron-job.org) with the secret in an Authorization header, since Vercel's
// own cron runs once a day on the Hobby plan — and each reader whose local
// clock has just passed one of their times gets one message for it.
//
// The same reminder goes by email too, to readers who tick that on the My
// page — to their own address, nobody else's. VAPID_SUBJECT is only the
// contact address the push services (Apple, Google, Mozilla) may write to
// about the sender; it never receives or sends a reminder.
//
//   POST /api/push?action=sub      { sub: PushSubscription.toJSON(), tz }   signed in
//   POST /api/push?action=unsub    { endpoint }                              signed in
//   GET  /api/push?action=key      the VAPID public key the browser subscribes with
//   GET  /api/push?action=remind   the cron (Authorization: Bearer CRON_SECRET)
//
// Environment: VAPID_PUBLIC_KEY, VAPID_PRIVATE_KEY (npx web-push
// generate-vapid-keys), VAPID_SUBJECT (a mailto: address), CRON_SECRET.
//
// userdata/<uid>/push.json:
//   { subs: { <id>: { endpoint, keys: { p256dh, auth }, tz, ua, at } },
//     sent: { "<local day>|am": <ts>, "<local day>|pm": <ts> } }

import crypto from "node:crypto";
import webpush from "web-push";
import { requireUser, listAccounts, r2GetJson, r2PutJson, userDataKey } from "../lib/auth.js";
import { siteName, isPublicSite } from "../lib/site.js";
import { sendEmail } from "../lib/admin/helpers.js";
import { goalsShortfall } from "../src/stats.js";

// The reminder can also go by email, to the reader's own address, when they
// have asked for that on the My page (goals.emailRemind). The time zone for a
// reader with no push device comes from their goals (goals.tz, set by the
// page from the device's clock).
const SITE_URL = isPublicSite() ? "https://samovar.live" : "https://govorim.dev";

function esc(t) { return String(t).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;" }[c]; }); }
function emailHtml(title, short, site) {
  return "<div style=\"font-family:Georgia,serif;font-size:16px;color:#1c1610;line-height:1.5\">" +
    "<p style=\"font-size:19px;margin:0 0 10px\"><b>" + esc(title) + "</b></p>" +
    "<ul style=\"margin:0 0 16px;padding-left:20px\">" + short.map(function (x) { return "<li>" + esc(x) + "</li>"; }).join("") + "</ul>" +
    "<p><a href=\"" + SITE_URL + "\" style=\"color:#7a2e2e\">Open " + esc(site) + "</a></p>" +
    "<p style=\"font-size:12px;color:#777\">You asked for these reminders on your My " + esc(site) + " page; turn them off there any time.</p></div>";
}

const WINDOW_MIN = 30;     // a time counts as "just passed" for this long — two missed cron runs
const DEFAULT_AM = "08:00";
const DEFAULT_PM = "17:00";

function vapidReady() {
  const pub = process.env.VAPID_PUBLIC_KEY, priv = process.env.VAPID_PRIVATE_KEY;
  if (!pub || !priv) return false;
  webpush.setVapidDetails(process.env.VAPID_SUBJECT || "mailto:hello@samovar.live", pub, priv);
  return true;
}

function subId(endpoint) {
  return crypto.createHash("sha1").update(String(endpoint)).digest("hex").slice(0, 16);
}

function cleanSub(s) {
  if (!s || typeof s !== "object") return null;
  const endpoint = String(s.endpoint || "");
  const keys = s.keys || {};
  if (!/^https:\/\/[^\s]{10,1000}$/.test(endpoint)) return null;
  if (!keys.p256dh || !keys.auth) return null;
  return { endpoint: endpoint, keys: { p256dh: String(keys.p256dh).slice(0, 200), auth: String(keys.auth).slice(0, 100) } };
}

function cleanTz(tz) {
  tz = String(tz || "").slice(0, 64);
  try { new Intl.DateTimeFormat("en-US", { timeZone: tz }); return tz; } catch (e) { return ""; }
}

// The reader's clock: their local day and minute-of-day in a time zone.
function localNow(tz, now) {
  try {
    const f = new Intl.DateTimeFormat("en-CA", { timeZone: tz, hour12: false, year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });
    const p = {};
    f.formatToParts(now).forEach(function (x) { p[x.type] = x.value; });
    return { day: p.year + "-" + p.month + "-" + p.day, min: ((Number(p.hour) || 0) % 24) * 60 + (Number(p.minute) || 0) };
  } catch (e) { return null; }
}

function minutesOf(hhmm) {
  const m = /^(\d{2}):(\d{2})$/.exec(String(hhmm || ""));
  return m ? (+m[1]) * 60 + (+m[2]) : null;
}

async function readPush(uid) {
  const p = (await r2GetJson(userDataKey(uid, "push")).catch(function () { return null; })) || {};
  return { subs: (p.subs && typeof p.subs === "object") ? p.subs : {}, sent: (p.sent && typeof p.sent === "object") ? p.sent : {} };
}

// One reader: which of their times has just passed on any of their devices,
// what to say, and the sending. Returns how many messages went out.
async function remindOne(account, now, site, canPushNow) {
  const push = await readPush(account.id);
  const ids = Object.keys(push.subs);
  const goals = (await r2GetJson(userDataKey(account.id, "goals")).catch(function () { return null; })) || {};
  if (!goals.notify) return 0;
  const byEmail = !!goals.emailRemind && /@/.test(String(account.email || ""));
  if (!ids.length && !byEmail) return 0;
  const times = { am: minutesOf(goals.remindAm || DEFAULT_AM), pm: minutesOf(goals.remind || DEFAULT_PM) };
  // The slots due now, by local day, over every device's clock: a reader with
  // a phone in one zone and a laptop in another is told once per slot per day.
  const due = {};
  const clocks = ids.map(function (id) { return (push.subs[id] && push.subs[id].tz) || "UTC"; });
  if (byEmail) clocks.push(cleanTz(goals.tz) || clocks[0] || "UTC");
  for (const tz of clocks) {
    const loc = localNow(tz, now);
    if (!loc) continue;
    for (const slot of ["am", "pm"]) {
      const t = times[slot];
      if (t == null) continue;
      if (loc.min >= t && loc.min < t + WINDOW_MIN) due[loc.day + "|" + slot] = { day: loc.day, slot: slot };
    }
  }
  const keys = Object.keys(due).filter(function (k) { return !push.sent[k]; });
  if (!keys.length) return 0;
  const stats = (await r2GetJson(userDataKey(account.id, "stats")).catch(function () { return null; })) || {};
  let changed = false, n = 0;
  for (const k of keys) {
    const d = due[k];
    const short = goalsShortfall(goals, stats[d.day] || {});
    push.sent[k] = now.getTime();
    changed = true;
    if (!short.length) continue;                   // nothing set, or every goal met: nothing to say
    const payload = d.slot === "am"
      ? { title: "Good morning — today's " + site + " goals", body: short.join(" · "), tag: "goals-am", url: "/" }
      : { title: "Still to do today on " + site, body: short.join(" · "), tag: "goals-pm", url: "/" };
    for (const id of (canPushNow ? ids : [])) {
      const s = push.subs[id];
      try {
        await webpush.sendNotification({ endpoint: s.endpoint, keys: s.keys }, JSON.stringify(payload), { TTL: 3 * 3600 });
        n++;
      } catch (e) {
        const code = (e && e.statusCode) || 0;
        if (code === 404 || code === 410) { delete push.subs[id]; changed = true; }   // the device unsubscribed
      }
    }
    if (byEmail) {
      const r = await sendEmail({ to: account.email, subject: payload.title, html: emailHtml(payload.title, short, site) }).catch(function () { return null; });
      if (r && r.sent) n++;
    }
  }
  // the record of what was sent, kept for two days
  const cutoff = now.getTime() - 2 * 86400000;
  for (const k of Object.keys(push.sent)) if ((Number(push.sent[k]) || 0) < cutoff) { delete push.sent[k]; changed = true; }
  if (changed) await r2PutJson(userDataKey(account.id, "push"), push);
  return n;
}

export default async function handler(req, res) {
  res.setHeader("Cache-Control", "no-store");
  const action = String((req.query && req.query.action) || "");

  if (action === "key") {
    if (!process.env.VAPID_PUBLIC_KEY) return res.status(503).json({ error: "Push is not set up on this site yet." });
    return res.status(200).json({ key: process.env.VAPID_PUBLIC_KEY });
  }

  if (action === "remind") {
    // The scheduler sends the secret as a bearer token (or ?secret=, for a
    // scheduler that cannot set a header); anything else is refused.
    const auth = String(req.headers.authorization || "");
    const given = auth.replace(/^Bearer\s+/i, "") || String((req.query && req.query.secret) || "");
    if (!process.env.CRON_SECRET || given !== process.env.CRON_SECRET) {
      return res.status(401).json({ error: "Not allowed" });
    }
    // Without VAPID keys the push side is skipped; email still goes.
    const canPush = vapidReady();
    const started = Date.now();
    const now = new Date();
    const site = siteName();
    let accounts = [];
    try { accounts = await listAccounts(); } catch (e) { return res.status(500).json({ error: "accounts: " + (e.message || e) }); }
    let sent = 0, readers = 0;
    // Six at a time, and done before the function's time is up.
    for (let i = 0; i < accounts.length; i += 6) {
      if (Date.now() - started > 50000) break;
      const batch = accounts.slice(i, i + 6).filter(function (a) { return a && a.approved; });
      const out = await Promise.all(batch.map(function (a) { return remindOne(a, now, site, canPush).catch(function () { return 0; }); }));
      out.forEach(function (k) { sent += k; readers++; });
    }
    return res.status(200).json({ ok: true, readers: readers, sent: sent });
  }

  // Everything else is a signed-in reader's own device.
  const user = requireUser(req, res);
  if (!user) return;
  if (req.method !== "POST") return res.status(405).json({ error: "POST" });
  let body = req.body;
  if (typeof body === "string") { try { body = JSON.parse(body); } catch (e) { body = {}; } }
  body = body || {};
  const key = userDataKey(user.id, "push");

  if (action === "sub") {
    const sub = cleanSub(body.sub);
    if (!sub) return res.status(400).json({ error: "Not a push subscription." });
    const push = await readPush(user.id);
    const id = subId(sub.endpoint);
    const cur = push.subs[id] || {};
    push.subs[id] = { endpoint: sub.endpoint, keys: sub.keys, tz: cleanTz(body.tz) || cur.tz || "UTC",
                      ua: String(req.headers["user-agent"] || "").slice(0, 160), at: Date.now() };
    // ten devices is plenty; the oldest goes
    const ids = Object.keys(push.subs).sort(function (a, b) { return (push.subs[b].at || 0) - (push.subs[a].at || 0); });
    ids.slice(10).forEach(function (k) { delete push.subs[k]; });
    await r2PutJson(key, push);
    return res.status(200).json({ ok: true, devices: Object.keys(push.subs).length });
  }

  if (action === "unsub") {
    const endpoint = String(body.endpoint || "");
    const push = await readPush(user.id);
    delete push.subs[subId(endpoint)];
    await r2PutJson(key, push);
    return res.status(200).json({ ok: true, devices: Object.keys(push.subs).length });
  }

  return res.status(404).json({ error: "Unknown action" });
}
