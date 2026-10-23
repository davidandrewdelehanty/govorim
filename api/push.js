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
import { goalsShortfall, goalsStatus } from "../src/stats.js";

// The reminder can also go by email, to the reader's own address, when they
// have asked for that on the My page (goals.emailRemind). The time zone for a
// reader with no push device comes from their goals (goals.tz, set by the
// page from the device's clock).
const SITE_URL = isPublicSite() ? "https://samovar.live" : "https://govorim.dev";

function esc(t) { return String(t).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;" }[c]; }); }
// The e-mailed reminder, set like the site: paper, ink, the rubric red, a
// serif — every goal that is set with its bar, what is left, and the way in.
// Tables and inline styles only, which is what mail clients render.
function fmt(n) { return String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g, ","); }
function emailHtml(kind, rows, site, dayLabel) {
  const PAPER = "#f4efe5", PAPER2 = "#ebe4d6", INK = "#1b1613", INK2 = "#6b625b", INK3 = "#8f867f",
        RULE = "#cfc6b8", RUBRIC = "#9b2d1f", GREEN = "#2f5a2a";
  const serif = "Georgia,'Times New Roman',Times,serif";
  const metN = rows.filter(function (r) { return r.met; }).length;
  const allMet = metN === rows.length;
  const title = kind === "am" ? "Good morning" : (allMet ? "Every goal met" : "Still to do today");
  const lead = kind === "am"
    ? "Today's goals on " + site + " — " + rows.length + (rows.length === 1 ? " thing" : " things") + " to do."
    : (allMet ? "All " + rows.length + " of today's goals are done." : (rows.length - metN) + " of " + rows.length + " still short, with the evening ahead.");
  const bar = function (r) {
    const pct = Math.max(0, Math.min(100, Math.round(100 * r.have / r.goal)));
    return "<table role=\"presentation\" width=\"100%\" cellpadding=\"0\" cellspacing=\"0\" style=\"border-collapse:collapse;margin:6px 0 0\"><tr>" +
      "<td style=\"background:" + PAPER2 + ";height:6px;line-height:6px;font-size:0;border-radius:3px\">" +
      "<div style=\"width:" + pct + "%;max-width:100%;height:6px;line-height:6px;font-size:0;background:" + (r.met ? GREEN : RUBRIC) + ";border-radius:3px\">&nbsp;</div>" +
      "</td></tr></table>";
  };
  const row = function (r) {
    const foot = r.met
      ? "<span style=\"color:" + GREEN + "\">Done &#10003;</span>"
      : fmt(r.left) + " " + esc(r.one + (r.left === 1 ? "" : "s")) + (r.what ? " " + esc(r.what) : "") + " to go";
    return "<tr><td style=\"padding:12px 0;border-bottom:1px solid " + RULE + "\">" +
      "<table role=\"presentation\" width=\"100%\" cellpadding=\"0\" cellspacing=\"0\" style=\"border-collapse:collapse\"><tr>" +
      "<td style=\"font-family:" + serif + ";font-size:16px;color:" + INK + "\">" + esc(r.label) + "</td>" +
      "<td align=\"right\" style=\"font-family:" + serif + ";font-size:15px;color:" + INK + ";white-space:nowrap\"><b>" + fmt(r.have) + "</b> <span style=\"color:" + INK3 + "\">/ " + fmt(r.goal) + "</span></td>" +
      "</tr></table>" + bar(r) +
      "<div style=\"font-family:" + serif + ";font-size:13px;color:" + INK2 + ";margin-top:5px\">" + foot + "</div>" +
      "</td></tr>";
  };
  return "<!doctype html><html><body style=\"margin:0;padding:0;background:" + PAPER + "\">" +
    "<table role=\"presentation\" width=\"100%\" cellpadding=\"0\" cellspacing=\"0\" style=\"border-collapse:collapse;background:" + PAPER + "\"><tr><td align=\"center\" style=\"padding:28px 14px\">" +
    "<table role=\"presentation\" width=\"100%\" cellpadding=\"0\" cellspacing=\"0\" style=\"border-collapse:collapse;max-width:560px\">" +
    // masthead
    "<tr><td style=\"padding:0 0 14px;border-bottom:1px solid " + INK + "\">" +
    "<span style=\"font-family:" + serif + ";font-size:24px;font-weight:bold;color:" + INK + "\">" + esc(site) + "</span>" +
    "<span style=\"font-family:Arial,Helvetica,sans-serif;font-size:11px;letter-spacing:2px;text-transform:uppercase;color:" + INK3 + ";padding-left:10px\">My " + esc(site) + "</span>" +
    "</td></tr>" +
    // kicker, title, lead
    "<tr><td style=\"padding:22px 0 0\">" +
    "<div style=\"font-family:Arial,Helvetica,sans-serif;font-size:11px;letter-spacing:2px;text-transform:uppercase;color:" + RUBRIC + "\">" + esc(dayLabel) + "</div>" +
    "<div style=\"font-family:" + serif + ";font-size:30px;line-height:1.15;color:" + INK + ";margin:6px 0 8px\">" + esc(title) + "</div>" +
    "<div style=\"font-family:" + serif + ";font-size:16px;line-height:1.5;color:" + INK2 + "\">" + esc(lead) + "</div>" +
    "</td></tr>" +
    // the goals
    "<tr><td style=\"padding:10px 0 0\"><table role=\"presentation\" width=\"100%\" cellpadding=\"0\" cellspacing=\"0\" style=\"border-collapse:collapse;border-top:1px solid " + RULE + "\">" +
    rows.map(row).join("") +
    "</table></td></tr>" +
    // the way in
    "<tr><td align=\"left\" style=\"padding:26px 0 0\">" +
    "<a href=\"" + SITE_URL + "\" style=\"display:inline-block;font-family:" + serif + ";font-size:16px;color:" + PAPER + ";background:" + INK + ";text-decoration:none;padding:12px 26px;border-radius:999px\">Open " + esc(site) + " &rarr;</a>" +
    "</td></tr>" +
    // foot
    "<tr><td style=\"padding:30px 0 0;font-family:" + serif + ";font-size:12px;line-height:1.6;color:" + INK3 + ";border-top:1px solid " + RULE + ";margin-top:30px\">" +
    "You asked for these reminders on your My " + esc(site) + " page, where the goals and the times are yours to change and the e-mail can be turned off." +
    "</td></tr>" +
    "</table></td></tr></table></body></html>";
}

// The e-mail for a day on which every goal that is set has been met — sent at
// the reminder time instead of the list of what is left. Mail clients run no
// script, so the balloons are emoji and the confetti is coloured shapes, set
// in rows above and below the words.
function congratsHtml(rows, site, dayLabel) {
  const PAPER = "#f4efe5", INK = "#1b1613", INK2 = "#6b625b", INK3 = "#8f867f", RULE = "#cfc6b8", RUBRIC = "#9b2d1f", GREEN = "#2f5a2a";
  const GOLD = "#c9962b", BLUE = "#2d5f8a", PLUM = "#7a3b6e";
  const serif = "Georgia,'Times New Roman',Times,serif";
  const colours = [RUBRIC, GOLD, GREEN, BLUE, PLUM, INK];
  const shapes = ["&#9632;", "&#9679;", "&#9650;", "&#9670;", "&#9733;", "&#9644;"];
  const confetti = function (seed, n) {
    let out = "";
    for (let i = 0; i < n; i++) {
      const k = (i * 7 + seed * 3) % 11;
      const col = colours[(i + seed) % colours.length], sh = shapes[(i * 5 + seed) % shapes.length];
      const size = 10 + (k % 4) * 3;
      const dy = (k % 3) * 5;
      out += "<span style=\"color:" + col + ";font-size:" + size + "px;position:relative;top:" + dy + "px;padding:0 " + (4 + (k % 3) * 3) + "px\">" + sh + "</span>";
    }
    return "<div style=\"text-align:center;line-height:26px;letter-spacing:2px;overflow:hidden\">" + out + "</div>";
  };
  const balloons = "<div style=\"text-align:center;font-size:44px;line-height:52px;padding:6px 0 0\">&#127880; &#127881; &#127880; &#127882; &#127880; &#127881; &#127880;</div>";
  const row = function (r) {
    return "<tr><td style=\"padding:10px 0;border-bottom:1px solid " + RULE + "\">" +
      "<table role=\"presentation\" width=\"100%\" cellpadding=\"0\" cellspacing=\"0\" style=\"border-collapse:collapse\"><tr>" +
      "<td style=\"font-family:" + serif + ";font-size:16px;color:" + INK + "\"><span style=\"color:" + GREEN + "\">&#10003;</span>&nbsp; " + esc(r.label) + "</td>" +
      "<td align=\"right\" style=\"font-family:" + serif + ";font-size:15px;color:" + INK + ";white-space:nowrap\"><b>" + fmt(r.have) + "</b> <span style=\"color:" + INK3 + "\">/ " + fmt(r.goal) + "</span></td>" +
      "</tr></table></td></tr>";
  };
  return "<!doctype html><html><body style=\"margin:0;padding:0;background:" + PAPER + "\">" +
    "<table role=\"presentation\" width=\"100%\" cellpadding=\"0\" cellspacing=\"0\" style=\"border-collapse:collapse;background:" + PAPER + "\"><tr><td align=\"center\" style=\"padding:28px 14px\">" +
    "<table role=\"presentation\" width=\"100%\" cellpadding=\"0\" cellspacing=\"0\" style=\"border-collapse:collapse;max-width:560px\">" +
    "<tr><td style=\"padding:0 0 14px;border-bottom:1px solid " + INK + "\">" +
    "<span style=\"font-family:" + serif + ";font-size:24px;font-weight:bold;color:" + INK + "\">" + esc(site) + "</span>" +
    "<span style=\"font-family:Arial,Helvetica,sans-serif;font-size:11px;letter-spacing:2px;text-transform:uppercase;color:" + INK3 + ";padding-left:10px\">My " + esc(site) + "</span>" +
    "</td></tr>" +
    "<tr><td style=\"padding:18px 0 0\">" + confetti(1, 22) + balloons + confetti(4, 22) + "</td></tr>" +
    "<tr><td align=\"center\" style=\"padding:10px 0 0\">" +
    "<div style=\"font-family:Arial,Helvetica,sans-serif;font-size:11px;letter-spacing:2px;text-transform:uppercase;color:" + RUBRIC + "\">" + esc(dayLabel) + "</div>" +
    "<div style=\"font-family:" + serif + ";font-size:34px;line-height:1.15;color:" + INK + ";margin:8px 0 10px\">Congratulations!</div>" +
    "<div style=\"font-family:" + serif + ";font-size:18px;line-height:1.5;color:" + INK2 + "\">All " + rows.length + (rows.length === 1 ? " goal was" : " goals were") + " met today. Well done &mdash; &#1073;&#1088;&#1072;&#1074;&#1086;!</div>" +
    "</td></tr>" +
    "<tr><td style=\"padding:18px 0 0\"><table role=\"presentation\" width=\"100%\" cellpadding=\"0\" cellspacing=\"0\" style=\"border-collapse:collapse;border-top:1px solid " + RULE + "\">" +
    rows.map(row).join("") +
    "</table></td></tr>" +
    "<tr><td style=\"padding:18px 0 0\">" + confetti(7, 22) + "</td></tr>" +
    "<tr><td align=\"center\" style=\"padding:14px 0 0\">" +
    "<a href=\"" + SITE_URL + "\" style=\"display:inline-block;font-family:" + serif + ";font-size:16px;color:" + PAPER + ";background:" + INK + ";text-decoration:none;padding:12px 26px;border-radius:999px\">Open " + esc(site) + " &rarr;</a>" +
    "</td></tr>" +
    "<tr><td style=\"padding:30px 0 0;font-family:" + serif + ";font-size:12px;line-height:1.6;color:" + INK3 + ";border-top:1px solid " + RULE + "\">" +
    "You asked for these e-mails on your My " + esc(site) + " page, where the goals, the times and this address are yours to change and the e-mail can be turned off. If this reached you by mistake, someone typed your address there; you can ignore it." +
    "</td></tr>" +
    "</table></td></tr></table></body></html>";
}

const WINDOW_MIN = 30;     // a time counts as "just passed" for this long — two missed cron runs
const DEFAULT_AM = "08:00";
const DEFAULT_PM = "17:00";

// Environment values, trimmed: a key pasted into Vercel with the line break
// after it is not the key — the browser refused the public one, and the cron
// secret never matched.
function env(name) { return String(process.env[name] || "").trim(); }

function vapidReady() {
  const pub = env("VAPID_PUBLIC_KEY"), priv = env("VAPID_PRIVATE_KEY");
  if (!pub || !priv) return false;
  webpush.setVapidDetails(env("VAPID_SUBJECT") || "mailto:hello@samovar.live", pub, priv);
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
  // the address on the account, or the one the reader typed on the My page
  const mailTo = /^[^\s@,;<>]+@[^\s@,;<>]+\.[^\s@,;<>]{2,}$/.test(String(goals.alertEmail || "")) ? String(goals.alertEmail) : String(account.email || "");
  const byEmail = !!goals.emailRemind && /@/.test(mailTo);
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
    const rec = stats[d.day] || {};
    const short = goalsShortfall(goals, rec);
    const rows = goalsStatus(goals, rec);
    push.sent[k] = now.getTime();
    changed = true;
    if (!rows.length) continue;                    // no goal is set: nothing to say
    // the day, as the My page writes it: "Thursday, 23 October"
    let dayLabel = "";
    try { dayLabel = new Date(d.day + "T12:00:00Z").toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long", timeZone: "UTC" }); } catch (e) {}
    if (!short.length) {
      // Every goal met at the reminder time: the congratulations go by e-mail
      // in place of the list of what is left.
      if (byEmail) {
        const r = await sendEmail({ to: mailTo, subject: "Congratulations \u2014 every " + site + " goal met today", html: congratsHtml(rows, site, dayLabel) }).catch(function () { return null; });
        if (r && r.sent) n++;
      }
      continue;
    }
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
      const r = await sendEmail({ to: mailTo, subject: payload.title, html: emailHtml(d.slot, rows, site, dayLabel) }).catch(function () { return null; });
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
    if (!env("VAPID_PUBLIC_KEY")) return res.status(503).json({ error: "Push is not set up on this site yet." });
    return res.status(200).json({ key: env("VAPID_PUBLIC_KEY") });
  }

  if (action === "remind") {
    // The scheduler sends the secret as a bearer token (or ?secret=, for a
    // scheduler that cannot set a header); anything else is refused.
    const auth = String(req.headers.authorization || "");
    const given = (auth.replace(/^Bearer\s+/i, "") || String((req.query && req.query.secret) || "")).trim();
    if (!env("CRON_SECRET") || given !== env("CRON_SECRET")) {
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
