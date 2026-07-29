// POST /api/admin/transcript-fbtext
// Admin-only. Returns the book's FB2 as a flat list of paragraphs (index, text,
// kind) so the Text editor can show the whole book and let the admin delete or
// edit paragraphs. Deletions/edits are committed back via transcript-apply's
// fb2Deletions (using { paraIdx } / { paraIdx, text }), which preserves the
// surrounding <section>/<title> structure.

import { requireAdmin } from "./_helpers.js";
import { loadParsedBook } from "./_book.js";

export default async function handler(req, res) {
  if (req.method !== "POST") return res.status(405).json({ error: "Method not allowed" });
  const a = await requireAdmin(req, res);
  if (!a) return;

  let body = req.body;
  if (typeof body === "string") { try { body = JSON.parse(body); } catch { body = {}; } }
  const fb2Path = body && body.fb2Path;
  if (!fb2Path || !/\.(fb2|epub)$/i.test(fb2Path)) return res.status(400).json({ error: "valid .fb2 or .epub path required" });

  try {
    const got = await loadParsedBook(fb2Path);
    if (!got) return res.status(404).json({ error: "Book not found" });
    const paras = got.parsed.paras.map(function (p, i) {
      return { i: i, text: p.text, kind: p.kind };
    });
    return res.status(200).json({ ok: true, paras: paras, count: paras.length, fb2Sha: got.sha, isEpub: got.isEpub });
  } catch (err) {
    return res.status(500).json({ error: (err && err.message) || "Failed to load FB2 text" });
  }
}
