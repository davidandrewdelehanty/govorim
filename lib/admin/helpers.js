// Shared admin-auth check: the caller must be signed in with the site's own
// session cookie AND be the admin (email matches ADMIN_EMAIL). Returns
// { ok, userId, email } or sends an error response and returns null.
//
// This used to verify a Clerk JWT from an Authorization header; the app now
// carries its own cookie session (lib/auth.js), so admin routes read that.
import { siteName } from "../site.js";
import { requireAdminUser } from "../auth.js";

export async function requireAdmin(req, res) {
  const user = requireAdminUser(req, res);
  if (!user) return null;
  return { ok: true, userId: user.id, email: user.email };
}

// Send an email via Resend if configured; silently no-op if not.
// Returns { sent: boolean, error?: string }.
export async function sendEmail({ to, subject, html }) {
  const apiKey = process.env.RESEND_API_KEY;
  if (!apiKey) return { sent: false, error: "RESEND_API_KEY not configured" };

  // The display name must stay ASCII: a raw Cyrillic name in the From header
  // is rejected by some senders unless MIME-encoded.
  const from = process.env.RESEND_FROM_EMAIL || (siteName() + " <onboarding@resend.dev>");
  try {
    const r = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + apiKey,
      },
      body: JSON.stringify({ from, to, subject, html }),
    });
    if (!r.ok) {
      const txt = await r.text();
      return { sent: false, error: "Resend " + r.status + ": " + txt.slice(0, 200) };
    }
    return { sent: true };
  } catch (err) {
    return { sent: false, error: err.message || String(err) };
  }
}
