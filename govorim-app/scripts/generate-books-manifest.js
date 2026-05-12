// Auto-generate public/books/index.json by scanning the books folder
// (and its category subfolders) for supported files.
// Runs automatically before every Vercel build (hooked in via the "prebuild" npm script),
// so dropping a new book into public/books/<category>/ and pushing is enough — no
// manual JSON edits.
//
// FOLDER CONVENTION (preferred):
//   public/books/novel/tolstoy-anna.epub      → category "Novel"
//   public/books/lyrics/tsoi-songs.epub       → category "Song Lyrics"
//   public/books/poetry/akhmatova.epub        → category "Poetry"
//   public/books/short-stories/chekhov.epub   → category "Short Stories"
//
// Files dropped directly into public/books/ (no subfolder) still work — they
// just go into the "Other" category until you move them. Any unknown subfolder
// is also treated as "Other".
//
// If you HAVE edited index.json by hand to set nice titles/authors/descriptions
// for a book, those edits are preserved: this script only ADDS entries for files
// that don't have one yet and REMOVES entries whose files no longer exist.

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

// Maps a subfolder name → category (the canonical name used in the picker).
// Add aliases here if you want to support multiple folder spellings for the
// same category.
const FOLDER_TO_CATEGORY = {
  "novel":         "Novel",
  "novels":        "Novel",
  "lyrics":        "Song Lyrics",
  "song-lyrics":   "Song Lyrics",
  "songs":         "Song Lyrics",
  "poetry":        "Poetry",
  "poems":         "Poetry",
  "short-stories": "Short Stories",
  "stories":       "Short Stories",
};

// Render order in the picker (must match the App.jsx CATEGORIES list).
const CATEGORY_ORDER = ["Novel", "Song Lyrics", "Poetry", "Short Stories"];

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

// 2. Scan the books folder AND its immediate subfolders for book files.
// Files in the root → no category prefix on filename, category unset (becomes "Other").
// Files in a subfolder → filename is "<subfolder>/<filename>", category looked up.
function scanForBooks() {
  const out = []; // { filename: "lyrics/tsoi.epub", subfolder: "lyrics" | null }
  let dirents;
  try {
    dirents = fs.readdirSync(booksDir, { withFileTypes: true });
  } catch (e) {
    console.error(`[books-manifest] Could not read ${booksDir}: ${e.message}`);
    process.exit(0); // Don't fail the build if the folder doesn't exist.
  }
  for (const d of dirents) {
    if (d.name.startsWith(".")) continue;
    if (d.isFile()) {
      if (SUPPORTED.test(d.name)) out.push({ filename: d.name, subfolder: null });
      continue;
    }
    if (d.isDirectory()) {
      // Only scan one level deep — keep the convention simple.
      let inner;
      try {
        inner = fs.readdirSync(path.join(booksDir, d.name), { withFileTypes: true });
      } catch (_) { continue; }
      for (const f of inner) {
        if (f.name.startsWith(".")) continue;
        if (f.isFile() && SUPPORTED.test(f.name)) {
          out.push({ filename: `${d.name}/${f.name}`, subfolder: d.name });
        }
      }
    }
  }
  return out;
}

const books = scanForBooks();

// 3. Build the new manifest. Existing entries keep their hand-set fields;
// new entries get auto-generated titles. Category is inferred from the
// subfolder unless manually set.
const next = books.map(({ filename, subfolder }) => {
  const inferredCategory = subfolder
    ? (FOLDER_TO_CATEGORY[subfolder.toLowerCase()] || "Other")
    : null;

  if (byFilename[filename]) {
    const e = byFilename[filename];
    // Preserve manual category; only fill in if missing.
    if (!e.category && inferredCategory) {
      return { ...e, category: inferredCategory };
    }
    return e;
  }

  const base = filename.split("/").pop();
  const stem = base.replace(/\.[^.]+$/, "").replace(/\.fb2$/i, "");
  const title = stem
    .replace(/[-_]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (c) => c.toUpperCase());

  const entry = { filename, title };
  if (inferredCategory) entry.category = inferredCategory;
  return entry;
});

// 4. Sort by category, then by title within each category.
const categoryRank = (c) => {
  const idx = CATEGORY_ORDER.indexOf(c);
  return idx === -1 ? CATEGORY_ORDER.length : idx;
};
next.sort((a, b) => {
  const ra = categoryRank(a.category);
  const rb = categoryRank(b.category);
  if (ra !== rb) return ra - rb;
  return (a.title || a.filename).localeCompare(b.title || b.filename, undefined, { sensitivity: "base" });
});

// 5. Report what changed.
const foundSet = new Set(books.map((b) => b.filename));
const added    = next.filter((n) => !byFilename[n.filename]).map((n) => n.filename);
const removed  = existing.filter((e) => !foundSet.has(e.filename)).map((e) => e.filename);

// 6. Write the manifest.
fs.writeFileSync(manifest, JSON.stringify(next, null, 2) + "\n", "utf8");
console.log(`[books-manifest] ${next.length} book${next.length === 1 ? "" : "s"} written to ${path.relative(projectDir, manifest)}`);
if (added.length)   console.log(`[books-manifest] Added:   ${added.join(", ")}`);
if (removed.length) console.log(`[books-manifest] Removed: ${removed.join(", ")}`);
