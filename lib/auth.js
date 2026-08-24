// Accounts and sessions, without a third-party auth service.
//
// Login is OPTIONAL on this site: reading works signed out. An account
// exists so vocabulary, tips and progress follow you between devices, and
// so the admin (ADMIN_EMAIL) can reach restricted books and the dashboard.
//
// Storage is the R2 bucket the app already uses for user data, so there is
// no second database to run:
//     userdata/accounts/<sha256(email)>.json   one account
//     userdata/accounts/_index.json            emails + ids, for the admin list
//
// A user id is derived from the email (u_<sha256(email)[0..23]>) rather than
// random, which means the same person always lands on the same
// userdata/<id>/ prefix -- an account can be deleted and recreated without
// orphaning the vocabulary behind it.
//
// Sessions are a signed cookie rather than a stored session row: payload +
// HMAC-SHA256 over it with AUTH_SECRET. Verifying costs no round trip, and
// changing AUTH_SECRET invalidates every session at once. The trade-off is
// that a session cannot be revoked individually before it expires; at this
// scale that is the right trade.

import crypto from "node:crypto";
import {
  S3Client, GetObjectCommand, PutObjectCommand,
} from "@aws-sdk/client-s3";

const BUCKET = process.env.R2_BUCKET || "govorim-audio";
const ACCOUNTS_PREFIX = "userdata/accounts";
const COOKIE_NAME = "gv_session";
const SESSION_DAYS = 30;

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

// ── small helpers ────────────────────────────────────────────────────────────

export function normalizeEmail(email) {
  return String(email || "").trim().toLowerCase();
}

export function userIdFor(email) {
  const h = crypto.createHash("sha256").update(normalizeEmail(email)).digest("hex");
  return "u_" + h.slice(0, 24);
}

function accountKey(email) {
  const h = crypto.createHash("sha256").update(normalizeEmail(email)).digest("hex");
  return `${ACCOUNTS_PREFIX}/${h}.json`;
}

export function isAdminEmail(email) {
  const admin = normalizeEmail(process.env.ADMIN_EMAIL);
  return !!admin && normalizeEmail(email) === admin;
}

function b64url(buf) {
  return Buffer.from(buf).toString("base64")
    .replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function fromB64url(str) {
  return Buffer.from(String(str).replace(/-/g, "+").replace(/_/g, "/"), "base64");
}

// ── R2 access ────────────────────────────────────────────────────────────────

async function r2GetJson(key) {
  try {
    const resp = await getS3().send(new GetObjectCommand({ Bucket: BUCKET, Key: key }));
    return JSON.parse(await resp.Body.transformToString());
  } catch (e) {
    if (e.name === "NoSuchKey" || e.$metadata?.httpStatusCode === 404) return null;
    throw e;
  }
}

async function r2PutJson(key, data) {
  await getS3().send(new PutObjectCommand({
    Bucket: BUCKET,
    Key: key,
    Body: JSON.stringify(data, null, 2),
    ContentType: "application/json",
  }));
}

// ── passwords ────────────────────────────────────────────────────────────────
//
// scrypt from node:crypto, so there is no native dependency to build on
// Vercel. Parameters are the Node defaults except for a raised cost: N=16384
// is ~100ms per hash on the function's CPU, slow enough to make a stolen
// hash expensive to attack and fast enough that a login does not time out.

const SCRYPT = { N: 16384, r: 8, p: 1, keylen: 64 };

function scryptHash(password, salt) {
  return new Promise(function (resolve, reject) {
    crypto.scrypt(password, salt, SCRYPT.keylen, SCRYPT, function (err, key) {
      if (err) reject(err); else resolve(key);
    });
  });
}

export async function hashPassword(password) {
  const salt = crypto.randomBytes(16);
  const key = await scryptHash(password, salt);
  return `scrypt$${SCRYPT.N}$${SCRYPT.r}$${SCRYPT.p}$${salt.toString("hex")}$${key.toString("hex")}`;
}

export async function verifyPassword(password, stored) {
  try {
    const parts = String(stored || "").split("$");
    if (parts.length !== 6 || parts[0] !== "scrypt") return false;
    const [, N, r, p, saltHex, keyHex] = parts;
    const salt = Buffer.from(saltHex, "hex");
    const expected = Buffer.from(keyHex, "hex");
    const actual = await new Promise(function (resolve, reject) {
      crypto.scrypt(password, salt, expected.length,
        { N: Number(N), r: Number(r), p: Number(p) },
        function (err, key) { if (err) reject(err); else resolve(key); });
    });
    // Constant-time: a length check first, because timingSafeEqual throws on
    // mismatched lengths and that throw would itself be a timing signal.
    if (actual.length !== expected.length) return false;
    return crypto.timingSafeEqual(actual, expected);
  } catch {
    return false;
  }
}

export function passwordProblem(password) {
  const pw = String(password || "");
  if (pw.length < 10) return "Password must be at least 10 characters.";
  if (pw.length > 200) return "Password must be under 200 characters.";
  // Deliberately no character-class rules: length is what matters, and
  // composition rules mostly produce Password1! and a sticky note.
  return null;
}

export function emailProblem(email) {
  const e = normalizeEmail(email);
  if (!e || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(e)) return "Enter a valid email address.";
  if (e.length > 254) return "That email address is too long.";
  return null;
}

// ── accounts ─────────────────────────────────────────────────────────────────

export async function findAccount(email) {
  return r2GetJson(accountKey(email));
}

// Accounts created from now on start unapproved and cannot sign in until an
// admin approves them. Accounts that predate this flow have no `approved`
// field at all, and `isApproved` treats a missing field as approved, so every
// existing reader is grandfathered in without a migration pass.
export function isApproved(account) {
  if (!account) return false;
  if (isAdminEmail(account.email)) return true;
  return account.approved !== false;
}

export async function setApproval(email, approved) {
  const account = await findAccount(email);
  if (!account) return { error: "No account with that email." };
  account.approved = !!approved;
  account.approvedAt = approved ? Date.now() : null;
  await r2PutJson(accountKey(account.email), account);
  return { account };
}

export async function createAccount(email, password) {
  const e = normalizeEmail(email);
  const existing = await findAccount(e);
  if (existing) return { error: "An account with that email already exists." };
  const account = {
    id: userIdFor(e),
    email: e,
    passwordHash: await hashPassword(password),
    createdAt: Date.now(),
    lastLoginAt: null,
    approved: isAdminEmail(e),
  };
  await r2PutJson(accountKey(e), account);
  await addToIndex(account);
  return { account };
}

export async function touchLogin(account) {
  account.lastLoginAt = Date.now();
  await r2PutJson(accountKey(account.email), account);
}

export async function setPassword(email, password) {
  const account = await findAccount(email);
  if (!account) return { error: "No account with that email." };
  account.passwordHash = await hashPassword(password);
  account.passwordChangedAt = Date.now();
  await r2PutJson(accountKey(account.email), account);
  return { account };
}

// The account index exists because the R2 API token is object-scoped -- it
// can read and write keys but cannot necessarily list the bucket -- so the
// admin user list is maintained here rather than discovered by a ListObjects
// call that may come back 403.
async function addToIndex(account) {
  const key = `${ACCOUNTS_PREFIX}/_index.json`;
  const index = (await r2GetJson(key)) || { users: [] };
  if (!index.users.some(function (u) { return u.email === account.email; })) {
    index.users.push({ id: account.id, email: account.email, createdAt: account.createdAt });
    await r2PutJson(key, index);
  }
}

export async function listAccounts() {
  const index = (await r2GetJson(`${ACCOUNTS_PREFIX}/_index.json`)) || { users: [] };
  const users = [];
  for (const entry of index.users) {
    const account = await findAccount(entry.email);
    if (!account) continue;
    users.push({
      id: account.id,
      email: account.email,
      createdAt: account.createdAt,
      lastLoginAt: account.lastLoginAt || null,
      isAdmin: isAdminEmail(account.email),
      approved: isApproved(account),
      grandfathered: account.approved === undefined && !isAdminEmail(account.email),
      approvedAt: account.approvedAt || null,
    });
  }
  users.sort(function (a, b) { return (b.createdAt || 0) - (a.createdAt || 0); });
  return users;
}

// ── sessions ─────────────────────────────────────────────────────────────────

function secret() {
  const s = process.env.AUTH_SECRET;
  if (!s || s.length < 16) return null;
  return s;
}

export function signSession(account) {
  const s = secret();
  if (!s) throw new Error("AUTH_SECRET not configured");
  const payload = {
    uid: account.id,
    email: account.email,
    exp: Date.now() + SESSION_DAYS * 24 * 60 * 60 * 1000,
  };
  const body = b64url(JSON.stringify(payload));
  const mac = b64url(crypto.createHmac("sha256", s).update(body).digest());
  return `${body}.${mac}`;
}

export function verifySessionToken(token) {
  const s = secret();
  if (!s || !token) return null;
  const dot = String(token).lastIndexOf(".");
  if (dot < 1) return null;
  const body = token.slice(0, dot);
  const mac = token.slice(dot + 1);
  const expected = crypto.createHmac("sha256", s).update(body).digest();
  const given = fromB64url(mac);
  if (given.length !== expected.length) return null;
  if (!crypto.timingSafeEqual(given, expected)) return null;
  let payload;
  try { payload = JSON.parse(fromB64url(body).toString("utf8")); } catch { return null; }
  if (!payload || !payload.uid || !payload.exp || Date.now() > payload.exp) return null;
  return payload;
}

function parseCookies(req) {
  const header = req.headers.cookie || "";
  const out = {};
  for (const part of header.split(";")) {
    const eq = part.indexOf("=");
    if (eq < 0) continue;
    out[part.slice(0, eq).trim()] = decodeURIComponent(part.slice(eq + 1).trim());
  }
  return out;
}

export function setSessionCookie(res, token) {
  const maxAge = SESSION_DAYS * 24 * 60 * 60;
  // HttpOnly so a script on the page cannot read it; SameSite=Lax so it
  // still rides along on ordinary navigations back to the site.
  res.setHeader("Set-Cookie",
    `${COOKIE_NAME}=${encodeURIComponent(token)}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=${maxAge}`);
}

export function clearSessionCookie(res) {
  res.setHeader("Set-Cookie",
    `${COOKIE_NAME}=; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=0`);
}

/** The signed-in user, or null. Never throws -- signed out is normal here. */
export function currentUser(req) {
  const payload = verifySessionToken(parseCookies(req)[COOKIE_NAME]);
  if (!payload) return null;
  return {
    id: payload.uid,
    email: payload.email,
    isAdmin: isAdminEmail(payload.email),
  };
}

/** Require any signed-in user; sends 401 and returns null if there is none. */
export function requireUser(req, res) {
  const user = currentUser(req);
  if (!user) {
    res.status(401).json({ error: "Not signed in" });
    return null;
  }
  return user;
}

/** Require the admin account; sends 401/403 and returns null otherwise. */
export function requireAdminUser(req, res) {
  if (!process.env.ADMIN_EMAIL) {
    res.status(500).json({ error: "ADMIN_EMAIL not configured" });
    return null;
  }
  const user = currentUser(req);
  if (!user) {
    res.status(401).json({ error: "Not signed in" });
    return null;
  }
  if (!user.isAdmin) {
    res.status(403).json({ error: "Admin access required" });
    return null;
  }
  return user;
}

export const SESSION_COOKIE_NAME = COOKIE_NAME;
