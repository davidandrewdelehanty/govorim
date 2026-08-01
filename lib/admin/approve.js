// approves or rejects a user.
// Body: { userId: string, action: "approve" | "reject" }
// On approve: sets publicMetadata.approved=true and emails the user.
// On reject:  sets publicMetadata.rejected=true (the user will keep
//             seeing the pending screen; you can also delete them
//             from the Clerk dashboard if you want them gone).
import { requireAdmin, getClerk, sendEmail } from "./helpers.js";

export async function handleApprove(req, res) {
  if (req.method !== "POST") return res.status(405).json({ error: "Method not allowed" });
  const a = await requireAdmin(req, res);
  if (!a) return;

  let body = req.body;
  if (typeof body === "string") {
    try { body = JSON.parse(body); } catch { body = {}; }
  }
  const { userId, action } = body || {};
  if (!userId || (action !== "approve" && action !== "reject")) {
    return res.status(400).json({ error: "Missing or invalid userId/action" });
  }

  try {
    const clerk = getClerk();
    const user = await clerk.users.getUser(userId);
    const email = user && user.primaryEmailAddress
      ? user.primaryEmailAddress.emailAddress
      : "";
    const firstName = user.firstName || "there";

    // Update Clerk metadata
    const newMeta = action === "approve"
      ? { approved: true, rejected: false, approvedAt: Date.now() }
      : { approved: false, rejected: true, rejectedAt: Date.now() };

    await clerk.users.updateUser(userId, { publicMetadata: newMeta });

    // Send email (only on approve, and only if Resend is configured).
    let emailResult = { sent: false };
    if (action === "approve" && email) {
      const appUrl = process.env.APP_URL || "https://your-app.vercel.app";
      emailResult = await sendEmail({
        to: email,
        subject: "You're approved on Говорим — start practicing Russian",
        html: `
<!DOCTYPE html>
<html>
<body style="font-family: Georgia, serif; background: #1a1611; color: #d2c5af; padding: 32px; max-width: 560px; margin: 0 auto;">
  <div style="background: #1f1c16; border: 1px solid rgba(210,197,175,0.14); border-radius: 16px; padding: 32px; text-align: center;">
    <h1 style="font-family: 'Playfair Display', Georgia, serif; color: #c8a276; font-size: 36px; margin: 0 0 8px;">Говорим</h1>
    <p style="color: rgba(210,197,175,0.6); font-size: 12px; letter-spacing: 2px; text-transform: uppercase; margin: 0 0 24px;">Russian Practice</p>
    <p style="font-size: 16px; line-height: 1.6;">Hi ${firstName},</p>
    <p style="font-size: 16px; line-height: 1.6;">Your account has been approved. You can now start practicing Russian — read EPUB books, get comprehension questions, and build your vocabulary.</p>
    <a href="${appUrl}" style="display: inline-block; background: linear-gradient(135deg, #9d4630, #82362a); color: #fff; padding: 14px 36px; text-decoration: none; border-radius: 10px; font-size: 16px; margin: 24px 0;">Open Говорим</a>
    <p style="font-size: 13px; color: rgba(210,197,175,0.5); margin-top: 24px;">Sign in with the Google account you used to register.</p>
  </div>
</body>
</html>`.trim(),
      });
    }

    return res.status(200).json({
      ok: true,
      userId,
      action,
      email,
      emailSent: emailResult.sent,
      emailError: emailResult.error || null,
    });
  } catch (err) {
    return res.status(500).json({ error: "Failed: " + (err.message || err) });
  }
}
