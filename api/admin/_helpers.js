// Shared admin-auth check: verifies the caller is signed in AND is the
// admin (their email matches ADMIN_EMAIL). Returns { ok, userId, email }
// or sends an error response and returns null.
import { verifyToken, createClerkClient } from "@clerk/backend";

let clerkClient = null;
export function getClerk() {
  if (!clerkClient) {
    clerkClient = createClerkClient({ secretKey: process.env.CLERK_SECRET_KEY });
  }
  return clerkClient;
}

export async function requireAdmin(req, res) {
  if (!process.env.CLERK_SECRET_KEY) {
    res.status(500).json({ error: "CLERK_SECRET_KEY not configured" });
    return null;
  }
  if (!process.env.ADMIN_EMAIL) {
    res.status(500).json({ error: "ADMIN_EMAIL not configured" });
    return null;
  }
  const auth = req.headers.authorization || "";
  if (!auth.startsWith("Bearer ")) {
    res.status(401).json({ error: "Not signed in" });
    return null;
  }
  const token = auth.slice(7).trim();
  let userId;
  try {
    const payload = await verifyToken(token, { secretKey: process.env.CLERK_SECRET_KEY });
    userId = payload && payload.sub;
    if (!userId) throw new Error("No user id in token");
  } catch (err) {
    res.status(401).json({ error: "Invalid or expired session" });
    return null;
  }
  try {
    const user = await getClerk().users.getUser(userId);
    const email = user && user.primaryEmailAddress
      ? (user.primaryEmailAddress.emailAddress || "").toLowerCase()
      : "";
    const adminEmail = (process.env.ADMIN_EMAIL || "").toLowerCase();
    if (!email || email !== adminEmail) {
      res.status(403).json({ error: "Admin access required" });
      return null;
    }
    return { ok: true, userId, email };
  } catch (err) {
    res.status(500).json({ error: "Could not verify admin: " + (err.message || err) });
    return null;
  }
}

// Send an email via Resend if configured; silently no-op if not.
// Returns { sent: boolean, error?: string }.
export async function sendEmail({ to, subject, html }) {
  const apiKey = process.env.RESEND_API_KEY;
  if (!apiKey) return { sent: false, error: "RESEND_API_KEY not configured" };

  const from = process.env.RESEND_FROM_EMAIL || "Govorим <onboarding@resend.dev>";
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
