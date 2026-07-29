// POST /api/admin/transcript-scan
// Admin-only. Aligns ONE audiobook chapter's transcript against the book's FB2
// and returns classified discrepancies for review. Stateless per call; the
// parsed FB2 is cached in module memory (keyed by sha) so a full-book scan
// doesn't re-tokenize 120k tokens on every chapter.
//
// Body: { fb2Path, chapterPath, chapterIndex, totalChapters }

import { requireAdmin } from "./_helpers.js";
import { ghGet } from "./_gh.js";
import { tokenizeFb2, scanChapter } from "./_talign.js";
import { loadParsedBook } from "./_book.js";

// Warm-invocation cache: bookPath → { sha, parsed, fbToks }
const fbCache = new Map();

async function getFb2(bookPath) {
  const got = await loadParsedBook(bookPath);
  if (!got) throw new Error("Book not found: " + bookPath);
  const cached = fbCache.get(bookPath);
  if (cached && cached.sha === got.sha) {
    return { sha: got.sha, parsed: cached.parsed, fbToks: cached.fbToks };
  }
  const fbToks = tokenizeFb2(got.parsed);
  fbCache.set(bookPath, { sha: got.sha, parsed: got.parsed, fbToks: fbToks });
  return { sha: got.sha, parsed: got.parsed, fbToks: fbToks };
}

export default async function handler(req, res) {
  if (req.method !== "POST") return res.status(405).json({ error: "Method not allowed" });
  const a = await requireAdmin(req, res);
  if (!a) return;

  let body = req.body;
  if (typeof body === "string") { try { body = JSON.parse(body); } catch { body = {}; } }
  const fb2Path = body && body.fb2Path;
  const chapterPath = body && body.chapterPath;
  const chapterIndex = body && body.chapterIndex != null ? body.chapterIndex : 0;
  const totalChapters = body && body.totalChapters != null ? body.totalChapters : 0;
  if (!fb2Path || !chapterPath) return res.status(400).json({ error: "fb2Path and chapterPath required" });
  if (!/\.(fb2|epub)$/i.test(fb2Path)) return res.status(400).json({ error: "Only .fb2 and .epub sources can be aligned." });

  try {
    const fb = await getFb2(fb2Path);
    const chGot = await ghGet(chapterPath);
    if (!chGot) return res.status(404).json({ error: "Chapter transcript not found: " + chapterPath });
    let js;
    try { js = JSON.parse(chGot.content); } catch (e) { return res.status(400).json({ error: "Chapter JSON parse failed" }); }

    const result = scanChapter(fb.parsed, fb.fbToks, js, chapterIndex, totalChapters);
    return res.status(200).json({
      ok: true,
      chapterIndex: chapterIndex,
      anchorOk: result.ok,
      anchor: result.anchor,
      summary: result.summary,
      discrepancies: result.discrepancies,
      fb2Sha: fb.sha,
      chapterSha: chGot.sha,
    });
  } catch (err) {
    return res.status(500).json({ error: (err && err.message) || "Scan failed" });
  }
}
