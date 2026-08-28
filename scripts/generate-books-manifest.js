// Auto-generate private/books/index.json by scanning BOTH book folders
// (and their category subfolders) for supported files.
//
// The manifest itself lives outside public/ because it is served by
// /api/catalogue, which strips restricted books unless the caller is the
// admin. A manifest published as a static asset would list every restricted
// title, author and chapter to anyone who asked for the file.
// Runs automatically before every Vercel build (hooked in via the "prebuild" npm script),
// so dropping a new book into public/books/<category>/ and pushing is enough — no
// manual JSON edits.
//
// FOLDER CONVENTION (preferred):
//   public/books/novel/tolstoy-anna.fb2       → category "Novels" (default for the prose/drama folder)
//   public/books/lyrics/tsoi-songs.epub       → category "Song Lyrics"
//   public/books/poetry/akhmatova.fb2         → category "Poetry"
//
// Files dropped directly into public/books/ (no subfolder) still work — they
// just go into the "Other" category until you move them. Any unknown subfolder
// is also treated as "Other".
//
// Two trees are scanned:
//   public/books/<category>/…   ordinary books, served as static assets
//   private/books/<category>/…  restricted books, reachable only through
//                               /api/media after an admin session check
// An entry from the private tree is marked "restricted": true, which is what
// /api/catalogue filters on. Move a file between the two trees and its
// restriction follows on the next build — the flag is derived, never hand-set.
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
const privateDir = path.join(projectDir, "private", "books");
const manifest   = path.join(privateDir, "index.json");

// Supported book formats (matches what the app's parseBook() can read).
// Longer extensions first so .fb2.zip matches before .fb2.
const SUPPORTED = /\.(fb2\.zip|epub|fb2|txt|html|htm|xhtml)$/i;

// Maps a subfolder name → category (the canonical name used in the picker).
// This only supplies a STARTING category for a file that has no manifest entry
// yet; books are classified by what they are (Novels, Novellas, Short Stories,
// Plays, Poetry, Religious Texts), and that classification is a hand-set field
// on the entry, which this script preserves. The "novel" folder holds all prose
// and drama, so a new file dropped there starts as "Novels" and gets corrected
// in index.json if it is actually a play or a story.
const FOLDER_TO_CATEGORY = {
  "novel":         "Novels",
  "novels":        "Novels",
  "works":         "Novels",
  "short-stories": "Short Stories",
  "stories":       "Short Stories",
  "plays":         "Plays",
  "play":          "Plays",
  "drama":         "Plays",
  "lyrics":        "Song Lyrics",
  "song-lyrics":   "Song Lyrics",
  "songs":         "Song Lyrics",
  "poetry":        "Poetry",
  "poems":         "Poetry",
};

// Render order in the picker (must match the App.jsx CATEGORIES list).
const CATEGORY_ORDER = ["Novels", "Novellas", "Short Stories", "Plays", "Poetry", "Song Lyrics", "Religious Texts", "Spectacle", "Speeches", "Speeches by Soviet Leaders", "Works"];

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
function scanForBooks(root, restricted) {
  const out = []; // { filename: "lyrics/tsoi.epub", subfolder: "lyrics" | null }
  let dirents;
  try {
    dirents = fs.readdirSync(root, { withFileTypes: true });
  } catch (e) {
    if (restricted) return out;  // no private tree yet — nothing restricted
    console.error(`[books-manifest] Could not read ${root}: ${e.message}`);
    process.exit(0); // Don't fail the build if the folder doesn't exist.
  }
  for (const d of dirents) {
    if (d.name.startsWith(".")) continue;
    if (d.isFile()) {
      if (SUPPORTED.test(d.name)) out.push({ filename: d.name, subfolder: null, restricted });
      continue;
    }
    if (d.isDirectory()) {
      // Only scan one level deep — keep the convention simple.
      let inner;
      try {
        inner = fs.readdirSync(path.join(root, d.name), { withFileTypes: true });
      } catch (_) { continue; }
      for (const f of inner) {
        if (f.name.startsWith(".")) continue;
        if (f.isFile() && SUPPORTED.test(f.name)) {
          out.push({ filename: `${d.name}/${f.name}`, subfolder: d.name, restricted });
        }
      }
    }
  }
  return out;
}

const books = scanForBooks(booksDir, false).concat(scanForBooks(privateDir, true));

// 3. Build the new manifest. Existing entries keep their hand-set fields;
// new entries get auto-generated titles. Category is inferred from the
// subfolder unless manually set.
const next = books.map(({ filename, subfolder, restricted }) => {
  const inferredCategory = subfolder
    ? (FOLDER_TO_CATEGORY[subfolder.toLowerCase()] || "Other")
    : null;

  if (byFilename[filename]) {
    const e = byFilename[filename];
    // Preserve manual category; only fill in if missing. The restricted flag
    // is always re-derived from which tree the file is in, so moving a book
    // in or out of private/ is the whole operation.
    const withCategory = (!e.category && inferredCategory)
      ? { ...e, category: inferredCategory }
      : { ...e };
    if (restricted) withCategory.restricted = true;
    else delete withCategory.restricted;
    return withCategory;
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
  if (restricted) entry.restricted = true;
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
fs.mkdirSync(path.dirname(manifest), { recursive: true });
fs.writeFileSync(manifest, JSON.stringify(next, null, 2) + "\n", "utf8");
console.log(`[books-manifest] ${next.length} book${next.length === 1 ? "" : "s"} written to ${path.relative(projectDir, manifest)}`);
const restrictedCount = next.filter((n) => n.restricted).length;
if (restrictedCount) console.log(`[books-manifest] ${restrictedCount} restricted (admin only)`);
if (added.length)   console.log(`[books-manifest] Added:   ${added.join(", ")}`);
if (removed.length) console.log(`[books-manifest] Removed: ${removed.join(", ")}`);
