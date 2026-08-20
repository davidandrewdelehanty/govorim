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

import {
  normalizeEmail, emailProblem, passwordProblem,
  findAccount, createAccount, verifyPassword, touchLogin,
  signSession, setSessionCookie, clearSessionCookie, currentUser,
} from "../lib/auth.js";

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
    return res.status(200).json({ user: currentUser(req) });
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
      setSessionCookie(res, signSession(account));
      return res.status(200).json({ user: publicUser(account) });
    }

    // login
    const account = await findAccount(email);
    // Same message and roughly the same work whether the account exists or
    // the password is wrong, so this cannot be used to enumerate accounts.
    const ok = account ? await verifyPassword(password, account.passwordHash) : false;
    if (!ok) {
      noteAttempt(ip);
      return res.status(401).json({ error: "Email or password is incorrect." });
    }
    await touchLogin(account);
    setSessionCookie(res, signSession(account));
    return res.status(200).json({ user: publicUser(account) });
  } catch (err) {
    return res.status(500).json({ error: "Auth failed: " + (err.message || err) });
  }
}
