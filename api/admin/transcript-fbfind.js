// POST /api/admin/transcript-fbfind
// Admin-only. Finds every occurrence of a phrase in a book's FB2 text and
// returns the token ranges + context, so the admin can remove specific
// passages by hand (for cases the automatic alignment doesn't surface —
// e.g. repeated refrains the diff slides across). The returned fbStart/fbEnd
// feed straight into transcript-apply's fb2Deletions.

import { requireAdmin } from "./_helpers.js";
import { tokenizeFb2, normWord } from "./_talign.js";
import { loadParsedBook } from "./_book.js";

export default async function handler(req, res) {
  if (req.method !== "POST") return res.status(405).json({ error: "Method not allowed" });
  const a = await requireAdmin(req, res);
  if (!a) return;

  let body = req.body;
  if (typeof body === "string") { try { body = JSON.parse(body); } catch { body = {}; } }
  const fb2Path = body && body.fb2Path;
  const query = (body && body.query ? String(body.query) : "").trim();
  if (!fb2Path || !/\.(fb2|epub)$/i.test(fb2Path)) return res.status(400).json({ error: "valid .fb2 or .epub path required" });
  if (!query) return res.status(400).json({ error: "query required" });

  try {
    const got = await loadParsedBook(fb2Path);
    if (!got) return res.status(404).json({ error: "Book not found" });
    const fbToks = tokenizeFb2(got.parsed);
    const fbNorms = fbToks.map(function (t) { return t.norm; });

    // normalized query tokens (skip tokens that normalize empty)
    const qTokens = query.split(/\s+/).map(normWord).filter(Boolean);
    if (!qTokens.length) return res.status(400).json({ error: "query has no searchable words" });
    const k = qTokens.length;

    const hits = [];
    for (let i = 0; i + k <= fbNorms.length; i++) {
      let ok = true;
      for (let t = 0; t < k; t++) { if (fbNorms[i + t] !== qTokens[t]) { ok = false; break; } }
      if (!ok) continue;
      const ctx = function (a2, b2) {
        const out = [];
        for (let j = Math.max(0, a2); j < Math.min(fbToks.length, b2); j++) out.push(fbToks[j].raw);
        return out.join(" ");
      };
      hits.push({
        fbStart: i, fbEnd: i + k,
        before: ctx(i - 8, i),
        match: ctx(i, i + k),
        after: ctx(i + k, i + k + 8),
        paraIdx: fbToks[i].paraIdx,
      });
      if (hits.length >= 200) break;
    }
    return res.status(200).json({ ok: true, count: hits.length, hits: hits, fb2Sha: got.sha });
  } catch (err) {
    return res.status(500).json({ error: (err && err.message) || "Search failed" });
  }
}
