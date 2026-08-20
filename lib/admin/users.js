// Lists the site's accounts. Admin only.
//
// Accounts live in R2 (see lib/auth.js) rather than in a third-party user
// directory, so this reads the account index and returns one row each. The
// approval flow is gone -- the site is public and an account only adds
// cross-device vocabulary -- so there is no approved/rejected state here.
import { requireAdmin } from "./helpers.js";
import { listAccounts } from "../auth.js";

export async function handleUsers(req, res) {
  if (req.method !== "GET") return res.status(405).json({ error: "Method not allowed" });
  const a = await requireAdmin(req, res);
  if (!a) return;

  try {
    const users = await listAccounts();
    return res.status(200).json({ users });
  } catch (err) {
    return res.status(500).json({ error: "Failed to list users: " + (err.message || err) });
  }
}
