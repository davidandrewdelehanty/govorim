// POST /api/admin/transcript-apply
// Admin-only. Applies a set of admin-approved edits and commits them to GitHub
// (which triggers a Vercel redeploy). Nothing is written unless it's in the
// request, and every changed file is backed up first (under _backups/) so any
// commit can be reverted.
//
// Body: {
//   fb2Path, fb2Sha,
//   fb2Inserts: [{ afterParaIdx, text }],
//   chapters: [{ path, sha, edits: [ {fragIdx,wIdx,newWord} | {run:{fragIdx,wStart,wEnd}, newWords:[...]} ] }],
//   backup: true
// }
//
// Concurrency/timeout note: commit a few chapters per call, not the whole book
// at once — each transcript file is 1-2 MB and every write is a separate commit.

import { requireAdmin } from "./_helpers.js";
import { ghGet, ghPut } from "./_gh.js";
import { parseFb2, tokenizeFb2, applyTranscriptEdits, applyFb2Edits } from "./_talign.js";

function backupPath(origPath, ts) {
  const flat = String(origPath).replace(/^public\/books\//, "").replace(/[\/]/g, "__");
  return "public/books/_backups/" + flat + "." + ts + ".bak";
}

function serializeLikeOriginal(originalText, obj) {
  // Preserve pretty-printing if the original was pretty-printed, else compact.
  const head = String(originalText || "").slice(0, 300);
  const pretty = /\{\s*\n\s+"/.test(head) || /\n\s{2,}"/.test(head);
  return pretty ? JSON.stringify(obj, null, 2) + "\n" : JSON.stringify(obj);
}

export default async function handler(req, res) {
  if (req.method !== "POST") return res.status(405).json({ error: "Method not allowed" });
  const a = await requireAdmin(req, res);
  if (!a) return;

  let body = req.body;
  if (typeof body === "string") { try { body = JSON.parse(body); } catch { body = {}; } }
  const doBackup = body.backup !== false;
  const ts = Date.now();
  const chapters = Array.isArray(body.chapters) ? body.chapters : [];
  const fb2Inserts = Array.isArray(body.fb2Inserts) ? body.fb2Inserts : [];

  const committed = [];
  const backups = [];
  const errors = [];

  try {
    // ---- Transcript (JSON) edits, per chapter ----
    for (let c = 0; c < chapters.length; c++) {
      const ch = chapters[c];
      if (!ch || !ch.path || !Array.isArray(ch.edits) || !ch.edits.length) continue;
      const got = await ghGet(ch.path);
      if (!got) { errors.push({ path: ch.path, error: "not found" }); continue; }
      if (ch.sha && got.sha !== ch.sha) {
        errors.push({ path: ch.path, error: "file changed since scan — re-scan this chapter", conflict: true });
        continue;
      }
      let js;
      try { js = JSON.parse(got.content); } catch (e) { errors.push({ path: ch.path, error: "JSON parse failed" }); continue; }

      const applied = applyTranscriptEdits(js, ch.edits);
      if (!applied.changed) { errors.push({ path: ch.path, error: "no edits applied (indices stale?)" }); continue; }

      // Safety guard: never commit a transcript whose word timings drifted.
      if (applied.integrity && !applied.integrity.ok) {
        errors.push({ path: ch.path, error: "timing-integrity check failed — not committed: " + applied.integrity.error, timing: true });
        continue;
      }

      if (doBackup) {
        const bp = backupPath(ch.path, ts);
        await ghPut(bp, got.content, null, "Backup " + ch.path + " before transcript fixes", );
        backups.push(bp);
      }
      const newText = serializeLikeOriginal(got.content, applied.js);
      await ghPut(ch.path, newText, got.sha, "Fix transcript: " + applied.changed + " edit(s) in " + ch.path.split("/").pop());
      committed.push({ path: ch.path, edits: applied.changed });
    }

    // ---- FB2 edits (insertions + deletions) ----
    const fb2Deletions = Array.isArray(body.fb2Deletions) ? body.fb2Deletions : [];
    if ((fb2Inserts.length || fb2Deletions.length) && body.fb2Path && /\.epub$/i.test(body.fb2Path)) {
      errors.push({ path: body.fb2Path, error: "Book-text edits (remove/insert) aren't supported for EPUB yet — transcript fixes were still applied." });
    } else if ((fb2Inserts.length || fb2Deletions.length) && body.fb2Path) {
      const got = await ghGet(body.fb2Path);
      if (!got) { errors.push({ path: body.fb2Path, error: "FB2 not found" }); }
      else if (body.fb2Sha && got.sha !== body.fb2Sha) {
        errors.push({ path: body.fb2Path, error: "FB2 changed since scan — re-scan before editing", conflict: true });
      } else {
        const parsed = parseFb2(got.content);
        const fbToks = tokenizeFb2(parsed);
        const out = applyFb2Edits(got.content, parsed, fbToks, fb2Inserts, fb2Deletions);
        if (out.count > 0) {
          if (doBackup) {
            const bp = backupPath(body.fb2Path, ts);
            await ghPut(bp, got.content, null, "Backup " + body.fb2Path + " before FB2 edits (" + out.inserts + " insert / " + out.deletions + " remove)");
            backups.push(bp);
          }
          const msgParts = [];
          if (out.inserts) msgParts.push("insert " + out.inserts + " passage(s)");
          if (out.deletions) msgParts.push("remove " + out.deletions + " passage(s)");
          await ghPut(body.fb2Path, out.raw, got.sha, "FB2 edits: " + msgParts.join(", ") + " in " + body.fb2Path.split("/").pop());
          committed.push({ path: body.fb2Path, inserts: out.inserts, deletions: out.deletions });
        } else {
          errors.push({ path: body.fb2Path, error: "no FB2 edits applied" });
        }
      }
    }

    return res.status(200).json({
      ok: errors.length === 0,
      committed: committed,
      backups: backups,
      errors: errors,
      message: committed.length
        ? (committed.length + " file(s) committed. Vercel redeploys in ~1-2 min.")
        : "Nothing committed.",
    });
  } catch (err) {
    return res.status(500).json({ error: (err && err.message) || "Apply failed", committed: committed, backups: backups, errors: errors });
  }
}
