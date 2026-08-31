// Sign-up / sign-in / sign-out / who-am-I, in one serverless function.
//
// One file rather than four because Vercel's Hobby plan caps a deployment at
// 12 functions and every .js under /api counts -- the same reason
// api/admin.js dispatches the whole admin dashboard. vercel.json rewrites
// /api/auth/<action> to this file with ?action=<action>.
//
// Login is optional on this site: everything readable works signed out, and
// an account only adds cross-device vocabulary plus, for ADMIN_EMAIL, the
// restricted books and the dashboard.
//
// Required env vars:
//   AUTH_SECRET            — long random string; signs session cookies.
//                            Changing it signs everybody out.
//   ADMIN_EMAIL            — the one account that gets admin rights.
//   R2_ENDPOINT, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY — account storage.

import { siteName, isPublicSite } from "../lib/site.js";

// Built once per instance, used when a login names an account that does not
// exist — see the login handler.
let decoyHash = null;
import {
  normalizeEmail,
  emailProblem,
  passwordProblem,
  findAccount,
  createAccount,
  verifyPassword,
  hashPassword,
  touchLogin,
  touchSeen,
  signSession,
  setSessionCookie,
  clearSessionCookie,
  currentUser,
  isApproved,
} from "../lib/auth.js";
import { sendEmail } from "../lib/admin/helpers.js";

// Best-effort brute-force damper. In-memory, so it resets on a cold start
// and is not shared between instances -- it raises the cost of guessing
// without pretending to be a real lockout.
const attempts = new Map();
const ATTEMPT_WINDOW_MS = 10 * 60 * 1000;
const MAX_ATTEMPTS = 10;

function clientIp(req) {
  const fwd = req.headers["x-forwarded-for"];
  if (typeof fwd === "string" && fwd.length) return fwd.split(",")[0].trim();
  return req.headers["x-real-ip"] || "unknown";
}

function tooManyAttempts(ip) {
  const now = Date.now();
  const hits = (attempts.get(ip) || []).filter(function (t) { return now - t < ATTEMPT_WINDOW_MS; });
  attempts.set(ip, hits);
  return hits.length >= MAX_ATTEMPTS;
}

function noteAttempt(ip) {
  const hits = attempts.get(ip) || [];
  hits.push(Date.now());
  attempts.set(ip, hits);
}

function readBody(req) {
  let body = req.body;
  if (typeof body === "string") {
    try { body = JSON.parse(body); } catch { body = {}; }
  }
  return body || {};
}

function publicUser(account) {
  return {
    id: account.id,
    email: account.email,
    isAdmin: normalizeEmail(account.email) === normalizeEmail(process.env.ADMIN_EMAIL),
  };
}

export default async function handler(req, res) {
  let action = req.query.action;
  if (Array.isArray(action)) action = action[0];

  if (action === "me") {
    const who = currentUser(req);
    if (!who) return res.status(200).json({ user: null });
    // Re-read the account so revoking approval takes effect on the next page
    // load rather than whenever the signed session happens to expire.
    try {
      const account = await findAccount(who.email);
      if (!account || !isApproved(account)) {
        clearSessionCookie(res);
        return res.status(200).json({ user: null, pending: !!account });
      }
    } catch (_) {
      // An R2 hiccup should not lock every reader out of the site, so fall
      // through and trust the signed session.
    }
    // Every page load by a signed-in reader counts as being seen. This runs
    // on each boot of the app, which is the only event that happens for
    // everyone — the old call site was the book-opening counter, so a reader
    // who signed in and browsed the library without opening anything showed
    // as never seen at all, which is most of what the panel was reporting.
    // touchSeen throttles itself, so this is a read on nearly every call and
    // a write only when the stored time has gone stale.
    try { await touchSeen(who.email); } catch (_) {}
    return res.status(200).json({ user: who });
  }

  if (action === "logout") {
    clearSessionCookie(res);
    return res.status(200).json({ ok: true });
  }

  if (action !== "signup" && action !== "login") {
    return res.status(404).json({ error: "Unknown auth action: " + (action || "(none)") });
  }
  if (req.method !== "POST") {
    return res.status(405).json({ error: "Method not allowed" });
  }
  if (!process.env.AUTH_SECRET) {
    return res.status(500).json({ error: "AUTH_SECRET not configured on the server" });
  }

  const ip = clientIp(req);
  if (tooManyAttempts(ip)) {
    return res.status(429).json({ error: "Too many attempts. Try again in a few minutes." });
  }

  const body = readBody(req);
  const email = normalizeEmail(body.email);
  const password = String(body.password || "");

  const badEmail = emailProblem(email);
  if (badEmail) return res.status(400).json({ error: badEmail });

  try {
    if (action === "signup") {
      const badPassword = passwordProblem(password);
      if (badPassword) return res.status(400).json({ error: badPassword });
      const { account, error } = await createAccount(email, password);
      if (error) return res.status(409).json({ error });
      // Tell the admin someone joined. Best-effort — a mail failure must never
      // break the signup — but log the reason, because a silent failure here is
      // indistinguishable from "nobody signed up".
      const notifyTo = process.env.FORUM_NOTIFY_EMAIL || process.env.ADMIN_EMAIL;
      if (notifyTo) {
        const safe = email.replace(/[&<>"]/g, "");
        try {
          const out = await sendEmail({
            to: notifyTo,
            subject: "[" + siteName() + "]" +
              (isPublicSite() ? " New reader: " : " Account awaiting approval: ") + safe,
            html: isPublicSite()
              ? "<p>A new reader signed up:</p><p><strong>" + safe + "</strong></p>" +
                "<p>Registration is open here, so they already have access.</p>"
              : "<p>A new reader signed up and is waiting for approval:</p>" +
                "<p><strong>" + safe + "</strong></p>" +
                "<p>They cannot sign in until you approve them in Manage Users.</p>",
          });
          if (out && out.sent === false) {
            console.error("[auth] signup notification not sent:", out.error);
          }
        } catch (err) {
          console.error("[auth] signup notification threw:", err && err.message);
        }
      } else {
        console.error("[auth] signup notification skipped: neither FORUM_NOTIFY_EMAIL nor ADMIN_EMAIL is set");
      }

      // New accounts wait for approval, so no session cookie is issued here.
      if (!isApproved(account)) {
        return res.status(200).json({
          pending: true,
          user: null,
          message: "Your account has been created and is waiting for approval.",
        });
      }
      // Record the signup as a use of the account. Without this a brand-new
      // reader carried a session while the panel showed a dash where their
      // last visit should be, and their login count sat at zero until the
      // cookie expired a month later and they signed in by hand.
      await touchLogin(account);
      setSessionCookie(res, signSession(account));
      return res.status(200).json({ user: publicUser(account) });
    }

    // login
    const account = await findAccount(email);
    // Same message AND the same work whether the account exists or the
    // password is wrong: a missing account still burns one scrypt against a
    // decoy hash, so response TIME cannot be used to enumerate accounts —
    // before this, the no-account path skipped scrypt and answered visibly
    // faster than a wrong password did.
    if (!decoyHash) decoyHash = await hashPassword("decoy-timing-pad");
    const ok = account
      ? await verifyPassword(password, account.passwordHash)
      : (await verifyPassword(password, decoyHash), false);
    if (!ok) {
      noteAttempt(ip);
      return res.status(401).json({ error: "Email or password is incorrect." });
    }
    if (!isApproved(account)) {
      return res.status(403).json({
        pending: true,
        error: "Your account is waiting for approval. You'll be able to sign in once it's approved.",
      });
    }
    await touchLogin(account);
    setSessionCookie(res, signSession(account));
    return res.status(200).json({ user: publicUser(account) });
  } catch (err) {
    return res.status(500).json({ error: "Auth failed: " + (err.message || err) });
  }
}
