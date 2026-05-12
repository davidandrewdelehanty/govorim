// /api/feedback.js
// User feedback button: signed-in users can send a short message; we forward
// it to ADMIN_EMAIL via Resend.

import { verifyToken, createClerkClient } from "@clerk/backend";
import { Resend } from "resend";

const clerk = createClerkClient({ secretKey: process.env.CLERK_SECRET_KEY });

const MAX_BODY = 2000;

function displayName(user) {
  const first = (user && user.firstName) || "";
  const last  = (user && user.lastName)  || "";
  const name  = (first + " " + last).trim();
  if (name) return name;
  return (user && user.primaryEmailAddress && user.primaryEmailAddress.emailAddress) || "Unknown";
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

export default async function handler(req, res) {
  if (req.method !== "POST") return res.status(405).json({ error: "Method not allowed" });

  const authHeader = req.headers.authorization || "";
  const token = authHeader.startsWith("Bearer ") ? authHeader.slice(7) : "";
  if (!token) return res.status(401).json({ error: "Not signed in" });

  let userId;
  try {
    const payload = await verifyToken(token, { secretKey: process.env.CLERK_SECRET_KEY });
    userId = payload && payload.sub;
  } catch (_) { return res.status(401).json({ error: "Invalid token" }); }
  if (!userId) return res.status(401).json({ error: "No user in token" });

  const body = typeof req.body === "string" ? JSON.parse(req.body) : (req.body || {});
  let message = String(body.message || "").trim();
  if (!message) return res.status(400).json({ error: "Message required" });
  if (message.length > MAX_BODY) message = message.slice(0, MAX_BODY);

  if (!process.env.RESEND_API_KEY)  return res.status(500).json({ error: "Email not configured (missing RESEND_API_KEY)" });
  if (!process.env.ADMIN_EMAIL)     return res.status(500).json({ error: "Admin email not set" });

  let me;
  try { me = await clerk.users.getUser(userId); }
  catch (_) { return res.status(401).json({ error: "User not found" }); }
  const fromName  = displayName(me);
  const fromEmail = (me.primaryEmailAddress && me.primaryEmailAddress.emailAddress) || "no-email";

  try {
    const resend = new Resend(process.env.RESEND_API_KEY);
    await resend.emails.send({
      from: "Говорим <onboarding@resend.dev>",
      to: process.env.ADMIN_EMAIL,
      replyTo: fromEmail,
      subject: "Говорим: feedback from " + fromName,
      html:
        '<div style="font-family:sans-serif;max-width:600px;margin:0 auto">' +
          '<h2 style="color:#c8a276">Feedback</h2>' +
          '<p><strong>From:</strong> ' + escapeHtml(fromName) + ' &lt;' + escapeHtml(fromEmail) + '&gt;</p>' +
          '<p><strong>User ID:</strong> ' + escapeHtml(userId) + '</p>' +
          '<hr>' +
          '<pre style="white-space:pre-wrap;font-family:sans-serif;font-size:14px;line-height:1.5">' + escapeHtml(message) + '</pre>' +
          '<p style="color:#888;font-size:11px;margin-top:24px">Reply directly to this email to respond to the user.</p>' +
        '</div>',
    });
  } catch (e) {
    return res.status(500).json({ error: e.message || "Failed to send" });
  }

  return res.status(200).json({ ok: true });
}
