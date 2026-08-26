// Diagnostic for the notification email. Admin only.
//
// A signup notification that never arrives looks exactly like nobody signing
// up, so this reports what the server is actually configured with and tries a
// real send, returning Resend's own error text when it fails.
import { siteName } from "../site.js";
import { requireAdmin, sendEmail } from "./helpers.js";

export async function handleMailTest(req, res) {
  const a = await requireAdmin(req, res);
  if (!a) return;

  const to = process.env.FORUM_NOTIFY_EMAIL || process.env.ADMIN_EMAIL || null;
  const config = {
    RESEND_API_KEY: process.env.RESEND_API_KEY ? "set" : "MISSING",
    RESEND_FROM_EMAIL: process.env.RESEND_FROM_EMAIL || ("(default: " + siteName() + " <onboarding@resend.dev>)"),
    FORUM_NOTIFY_EMAIL: process.env.FORUM_NOTIFY_EMAIL || "(not set)",
    ADMIN_EMAIL: process.env.ADMIN_EMAIL || "(not set)",
    willSendTo: to || "NOBODY — set FORUM_NOTIFY_EMAIL or ADMIN_EMAIL",
  };
  if (!to) return res.status(200).json({ ok: false, config });

  const result = await sendEmail({
    to,
    subject: "[" + siteName() + "] Test notification",
    html: "<p>This is the notification test from Manage Users. If you are reading it, signup emails will arrive too.</p>",
  });
  return res.status(200).json({ ok: !!result.sent, config, result });
}
