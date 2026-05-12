// Serverless function: scans public/books/ at request time and returns
// a list of available preloaded books. Drop a supported file into
// public/books/, push to GitHub, and the next page load shows it in
// the dropdown — no manifest script needed.
//
// If public/books/index.json exists, manual overrides there
// (nicer title, author, description, splitByNumberedSections) take
// precedence over auto-derived titles. Files in the folder without a
// matching entry get a title derived from their filename.
//
// Vercel only mounts files this function explicitly opts into via
// `includeFiles` — see vercel.json.

import fs from "node:fs";
import path from "node:path";

// Longer extensions first so .fb2.zip matches before .fb2.
const SUPPORTED = /\.(fb2\.zip|epub|fb2|txt|html|htm|xhtml)$/i;

function deriveTitle(filename) {
  const stem = filename.replace(/\.[^.]+$/, "").replace(/\.fb2$/i, "");
  return stem
    .replace(/[-_]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, function (c) { return c.toUpperCase(); });
}

export default function handler(req, res) {
  try {
    const booksDir = path.join(process.cwd(), "public", "books");

    // Load manual overrides from index.json if present (optional).
    let overrides = {};
    try {
      const raw = fs.readFileSync(path.join(booksDir, "index.json"), "utf8");
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) {
        overrides = Object.fromEntries(
          parsed.map(function (e) { return [e.filename, e]; })
        );
      }
    } catch (_) {
      // No manifest — fine, we'll derive everything from filenames.
    }

    // Scan the folder for actual book files.
    const files = fs.readdirSync(booksDir)
      .filter(function (f) { return !f.startsWith(".") && SUPPORTED.test(f); })
      .sort();

    // Merge: use manual override if available, else derive from filename.
    const books = files.map(function (filename) {
      if (overrides[filename]) return overrides[filename];
      return { filename: filename, title: deriveTitle(filename) };
    });

    // Sort alphabetically by display title (case-insensitive, locale-aware).
    books.sort(function (a, b) {
      return (a.title || a.filename).localeCompare(
        b.title || b.filename, undefined, { sensitivity: "base" }
      );
    });

    // Cache briefly at the edge so we're not hammering the FS on every load.
    res.setHeader("Cache-Control", "public, max-age=60, s-maxage=60");
    res.status(200).json(books);
  } catch (e) {
    res.status(500).json({ error: (e && e.message) || "Failed to list books" });
  }
}
