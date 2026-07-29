// GET /api/admin/transcript-books
// Admin-only. Returns the list of audiobooks (library entries that have an
// audiobook.chapters transcript list) for the Transcript Tools dashboard.

import { requireAdmin } from "./_helpers.js";
import { ghGet } from "./_gh.js";

export default async function handler(req, res) {
  if (req.method !== "GET") return res.status(405).json({ error: "Method not allowed" });
  const a = await requireAdmin(req, res);
  if (!a) return;

  try {
    const idx = await ghGet("public/books/index.json");
    let arr = [];
    if (idx) { try { arr = JSON.parse(idx.content); } catch { arr = []; } }
    if (!Array.isArray(arr)) arr = [];

    const books = [];
    for (let i = 0; i < arr.length; i++) {
      const e = arr[i];
      const ab = e && e.audiobook;
      const chapters = ab && Array.isArray(ab.chapters) ? ab.chapters : null;
      if (!chapters || !chapters.length) continue;
      const filename = e.filename || "";
      const isFb2 = /\.fb2$/i.test(filename);
      const isEpub = /\.epub$/i.test(filename);
      books.push({
        title: e.title || filename,
        author: e.author || "",
        filename: filename,
        fb2Path: "public/books/" + filename,
        supported: isFb2 || isEpub,
        isEpub: isEpub,
        note: (isFb2 || isEpub) ? (isEpub ? "EPUB: scanning + transcript fixes work; book-text edits (remove/insert) are FB2-only for now." : "") : "Alignment needs an .fb2 or .epub source (this book is " + (filename.split(".").pop() || "?") + ").",
        narrator: (ab && ab.narrator) || "",
        chapters: chapters.map(function (c, ci) {
          return { index: ci, path: "public/books/" + c, name: String(c).split("/").pop() };
        }),
        nChapters: chapters.length,
      });
    }
    return res.status(200).json({ ok: true, books: books });
  } catch (err) {
    return res.status(500).json({ error: (err && err.message) || "Failed to list audiobooks" });
  }
}
