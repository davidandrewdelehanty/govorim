// /api/clerk-webhook.js
// Receives webhooks from Clerk and emails the admin when a new user signs up.
//
// Setup (one-time, in Clerk Dashboard → Webhooks):
//   1. Add endpoint URL:       https://govorim.vercel.app/api/clerk-webhook
//   2. Subscribe to events:    user.created
//   3. Copy the Signing Secret
//   4. Add to Vercel as env var: CLERK_WEBHOOK_SECRET
//
// The signature is verified with svix using that secret so a random POST
// to this endpoint can't trigger emails.

import { Webhook } from "svix";
import { Resend } from "resend";

// Vercel parses JSON bodies by default, but webhook signature verification
// needs the EXACT raw body. Turn off the parser for this route.
export const config = { api: { bodyParser: false } };

async function readRawBody(req) {
  const chunks = [];
  for await (const chunk of req) chunks.push(typeof chunk === "string" ? Buffer.from(chunk) : chunk);
  return Buffer.concat(chunks).toString("utf8");
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

export default async function handler(req, res) {
  if (req.method !== "POST") return res.status(405).json({ error: "Method not allowed" });

  if (!process.env.CLERK_WEBHOOK_SECRET) {
    return res.status(500).json({ error: "CLERK_WEBHOOK_SECRET not set" });
  }

  // Read raw body and verify signature
  const rawBody = await readRawBody(req);
  const headers = {
    "svix-id":        req.headers["svix-id"],
    "svix-timestamp": req.headers["svix-timestamp"],
    "svix-signature": req.headers["svix-signature"],
  };

  let evt;
  try {
    const wh = new Webhook(process.env.CLERK_WEBHOOK_SECRET);
    evt = wh.verify(rawBody, headers);
  } catch (e) {
    return res.status(401).json({ error: "Bad signature" });
  }

  // Only react to user.created
  if (!evt || evt.type !== "user.created") {
    return res.status(200).json({ ok: true, ignored: true });
  }

  const data = evt.data || {};
  const first  = data.first_name || "";
  const last   = data.last_name  || "";
  const name   = (first + " " + last).trim() || "(no name set)";
  const email  = (data.email_addresses && data.email_addresses[0] && data.email_addresses[0].email_address) || "(no email)";
  const userId = data.id || "(unknown)";
  const created = data.created_at ? new Date(data.created_at).toUTCString() : "(unknown)";
  const appUrl  = process.env.APP_URL || "https://govorim.vercel.app";

  // Send admin email
  if (!process.env.RESEND_API_KEY || !process.env.ADMIN_EMAIL) {
    // No email configured — log + 200 so Clerk doesn't retry forever.
    console.log("[clerk-webhook] new user", { name, email, userId });
    return res.status(200).json({ ok: true, emailed: false });
  }

  try {
    const resend = new Resend(process.env.RESEND_API_KEY);
    await resend.emails.send({
      from: "Говорим <onboarding@resend.dev>",
      to: process.env.ADMIN_EMAIL,
      subject: "Говорим: New user awaiting approval — " + name,
      html:
        '<div style="font-family:sans-serif;max-width:600px;margin:0 auto;background:#1f1c16;color:#d2c5af;padding:32px;border-radius:14px">' +
          '<h1 style="font-family:Georgia,serif;color:#c8a276;margin:0 0 16px">Говорим</h1>' +
          '<p style="font-size:16px">Someone just signed up. They\'re waiting for you to approve their account.</p>' +
          '<div style="background:rgba(200,162,118,0.08);border:1px solid rgba(200,162,118,0.3);border-radius:10px;padding:16px;margin:20px 0">' +
            '<p style="margin:4px 0"><strong>Name:</strong> ' + escapeHtml(name) + '</p>' +
            '<p style="margin:4px 0"><strong>Email:</strong> ' + escapeHtml(email) + '</p>' +
            '<p style="margin:4px 0;font-size:12px;color:rgba(210,197,175,0.5)"><strong>Signed up:</strong> ' + escapeHtml(created) + '</p>' +
            '<p style="margin:4px 0;font-size:11px;color:rgba(210,197,175,0.4)"><strong>User ID:</strong> ' + escapeHtml(userId) + '</p>' +
          '</div>' +
          '<p style="text-align:center;margin-top:24px">' +
            '<a href="' + appUrl + '" style="background:#9d4630;color:#fff;text-decoration:none;padding:12px 24px;border-radius:8px;font-weight:600;display:inline-block">Open Говорим to approve</a>' +
          '</p>' +
          '<p style="color:rgba(210,197,175,0.5);font-size:11px;margin-top:32px">Open the app, then tap the 👥 Users button to approve or reject.</p>' +
        '</div>',
    });
  } catch (e) {
    // Log but return 200 — we don't want Clerk to keep retrying if email fails
    console.error("[clerk-webhook] email send failed:", e.message);
  }

  return res.status(200).json({ ok: true });
}
