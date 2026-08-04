// Single consolidated admin function. Vercel's Hobby plan caps a deployment at
// 12 Serverless Functions; the admin dashboard alone used to be 9 separate
// files (plus 5 more shared-helper files that ALSO each counted as their own
// function, since Vercel deploys every .js file under /api regardless of an
// underscore prefix — that convention does NOT exclude a file from being
// built as a function). Fixed by moving all the actual logic to /lib/admin
// (outside /api, so it's just imported code, never its own function) and
// routing every /api/admin/<action> URL to this one file via the rewrite in
// vercel.json: { "source": "/api/admin/:action*", "destination":
// "/api/admin?action=:action*" }. The client's fetch() calls did not change —
// they still hit /api/admin/approve, /api/admin/upload-book, etc.; Vercel
// rewrites those to this function with req.query.action set to the action
// name, and this dispatcher calls the matching handler.

import { handleApprove }          from "../lib/admin/approve.js";
import { handleUsers }            from "../lib/admin/users.js";
import { handleUploadBook }       from "../lib/admin/upload-book.js";
import { handleUploadSong }       from "../lib/admin/upload-song.js";

const ROUTES = {
  "approve":            handleApprove,
  "users":              handleUsers,
  "upload-book":        handleUploadBook,
  "upload-song":        handleUploadSong,
};

export default async function handler(req, res) {
  let action = req.query.action;
  if (Array.isArray(action)) action = action[0];
  const fn = action && ROUTES[action];
  if (!fn) {
    return res.status(404).json({ error: "Unknown admin action: " + (action || "(none)") });
  }
  return fn(req, res);
}
