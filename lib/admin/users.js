// Lists the site's accounts and approves or revokes them. Admin only.
//
// Accounts live in R2 (see lib/auth.js) rather than in a third-party user
// directory, so this reads the account index and returns one row each.
// New accounts start unapproved and cannot sign in until approved here;
// accounts that predate the approval flow have no `approved` field and are
// treated as approved, so existing readers keep working untouched.
import { requireAdmin } from "./helpers.js";
import { listAccounts, setApproval, isAdminEmail } from "../auth.js";

export async function handleUsers(req, res) {
  const a = await requireAdmin(req, res);
  if (!a) return;

  if (req.method === "GET") {
    try {
      const users = await listAccounts();
      return res.status(200).json({ users });
    } catch (err) {
      return res.status(500).json({ error: "Failed to list users: " + (err.message || err) });
    }
  }

  if (req.method === "POST") {
    let body = req.body;
    if (typeof body === "string") { try { body = JSON.parse(body); } catch (_) { body = {}; } }
    body = body || {};
    const email = String(body.email || "").trim().toLowerCase();
    if (!email) return res.status(400).json({ error: "email is required" });
    if (isAdminEmail(email)) {
      return res.status(400).json({ error: "The admin account cannot be changed here." });
    }
    const approved = body.approved !== false;
    try {
      const { error } = await setApproval(email, approved);
      if (error) return res.status(404).json({ error });
      const users = await listAccounts();
      return res.status(200).json({ ok: true, users });
    } catch (err) {
      return res.status(500).json({ error: "Failed to update user: " + (err.message || err) });
    }
  }

  return res.status(405).json({ error: "Method not allowed" });
}
