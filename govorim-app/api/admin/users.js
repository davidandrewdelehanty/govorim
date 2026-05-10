// GET /api/admin/users — returns a list of all signed-up users with
// their approval status. Admin only.
import { requireAdmin, getClerk } from "./_helpers.js";

export default async function handler(req, res) {
  if (req.method !== "GET") return res.status(405).json({ error: "Method not allowed" });
  const a = await requireAdmin(req, res);
  if (!a) return;

  try {
    // Fetch up to 100 users (Clerk default cap is 10, request more)
    const list = await getClerk().users.getUserList({ limit: 100, orderBy: "-created_at" });
    const users = (list.data || list).map(function(u) {
      const email = u.primaryEmailAddress ? u.primaryEmailAddress.emailAddress : "";
      const meta = u.publicMetadata || {};
      return {
        id: u.id,
        email: email,
        firstName: u.firstName || "",
        lastName: u.lastName || "",
        imageUrl: u.imageUrl || "",
        createdAt: u.createdAt,
        approved: meta.approved === true,
        rejected: meta.rejected === true,
        isAdmin: email.toLowerCase() === (process.env.ADMIN_EMAIL || "").toLowerCase(),
      };
    });
    return res.status(200).json({ users });
  } catch (err) {
    return res.status(500).json({ error: "Failed to list users: " + (err.message || err) });
  }
}
