// Auto-generate public/books/index.json by scanning the books folder for supported files.
// Runs automatically before every Vercel build (hooked in via the "prebuild" npm script),
// so dropping a new EPUB into public/books/ and pushing is enough — no manual JSON edits.
//
// If you HAVE edited index.json by hand to set nice titles/authors/descriptions for a book,
// those edits are preserved: this script only ADDS entries for files that don't have one yet
// and REMOVES entries whose files no longer exist.

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname  = path.dirname(fileURLToPath(import.meta.url));
const projectDir = path.resolve(__dirname, "..");
const booksDir   = path.join(projectDir, "public", "books");
const manifest   = path.join(booksDir, "index.json");

// Supported book formats (matches what the app's parseBook() can read).
// Longer extensions first so .fb2.zip matches before .fb2.
const SUPPORTED = /\.(fb2\.zip|epub|fb2|txt|html|htm|xhtml)$/i;

// 1. Load any existing manifest so we keep manual metadata edits.
let existing = [];
try {
  const raw = fs.readFileSync(manifest, "utf8");
  const parsed = JSON.parse(raw);
  if (Array.isArray(parsed)) existing = parsed;
} catch (_) {
  // No manifest yet — that's fine, we'll create one.
}
const byFilename = Object.fromEntries(existing.map((e) => [e.filename, e]));

// 2. Scan the folder for actual book files.
let dirents;
try {
  dirents = fs.readdirSync(booksDir);
} catch (e) {
  console.error(`[books-manifest] Could not read ${booksDir}: ${e.message}`);
  process.exit(0); // Don't fail the build if the folder doesn't exist.
}
const files = dirents
  .filter((f) => !f.startsWith("."))       // skip hidden files
  .filter((f) => SUPPORTED.test(f))         // only book formats
  .sort();

// 3. Build the new manifest: keep existing entries, add minimal entries for new files.
const next = files.map((filename) => {
  if (byFilename[filename]) return byFilename[filename];
  // Auto-derive a readable title from the filename.
  const stem = filename.replace(/\.[^.]+$/, "").replace(/\.fb2$/i, "");
  const title = stem
    .replace(/[-_]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (c) => c.toUpperCase());
  return { filename, title };
});

// 4. Sort by title (case-insensitive, locale-aware) so the dropdown reads alphabetically.
next.sort((a, b) =>
  (a.title || a.filename).localeCompare(b.title || b.filename, undefined, { sensitivity: "base" })
);

// 5. Report what changed.
const added   = next.filter((n) => !byFilename[n.filename]).map((n) => n.filename);
const removed = existing.filter((e) => !files.includes(e.filename)).map((e) => e.filename);

// 6. Write the manifest.
fs.writeFileSync(manifest, JSON.stringify(next, null, 2) + "\n", "utf8");
console.log(`[books-manifest] ${next.length} book${next.length === 1 ? "" : "s"} written to ${path.relative(projectDir, manifest)}`);
if (added.length)   console.log(`[books-manifest] Added:   ${added.join(", ")}`);
if (removed.length) console.log(`[books-manifest] Removed: ${removed.join(", ")}`);
