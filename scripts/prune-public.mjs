#!/usr/bin/env node
// Remove private material from the build output before it is deployed.
//
// WHY THIS EXISTS, and why filtering the catalogue is not enough:
//
// /api/catalogue can hide a book from the picker, but the files it points at
// live in public/ and are served straight off the CDN with no session check.
// Hiding the entry leaves samovar.live/books/petushki-en/01.json returning the
// text to anyone who guesses the path. Filtering a list does not unpublish a
// file.
//
// So on the public build the files are not shipped at all. Vercel runs a
// separate build per project with that project's environment, so this prunes
// dist/ only when SITE_MODE=public and leaves the private deployment whole.
//
// It runs against dist/, never against public/ — the working tree is not
// touched and a bad run is fixed by rebuilding.
//
//   node scripts/prune-public.mjs [--dry-run]

import fs from "node:fs";
import path from "node:path";

const DRY = process.argv.includes("--dry-run");
const ROOT = process.cwd();
const DIST = path.join(ROOT, "dist");
const MANIFEST = path.join(ROOT, "private", "books", "index.json");

if (process.env.SITE_MODE !== "public") {
  console.log("[prune] SITE_MODE is not \"public\" — private build, nothing pruned.");
  process.exit(0);
}

if (!fs.existsSync(DIST)) {
  console.error("[prune] FATAL: dist/ not found. This must run after the build.");
  process.exit(1);
}

// Refusing to deploy is the right failure here. A missing manifest with no
// allowlist would otherwise mean shipping the entire private library.
let manifest;
try {
  manifest = JSON.parse(fs.readFileSync(MANIFEST, "utf8"));
} catch (e) {
  console.error("[prune] FATAL: cannot read the catalogue manifest: " + (e.message || e));
  console.error("[prune] Refusing to produce a public build without an allowlist.");
  process.exit(1);
}
if (!Array.isArray(manifest)) {
  console.error("[prune] FATAL: manifest is not an array.");
  process.exit(1);
}

// A book ships publicly only if it says so. Absent flag means private, and a
// restricted book is never public regardless.
const publicEntries = manifest.filter((e) => e && e.public === true && !e.restricted);

console.log("[prune] SITE_MODE=public — " + publicEntries.length + " of " +
            manifest.length + " catalogue entries are marked public.");
if (!publicEntries.length) {
  console.warn("[prune] WARNING: no entry has \"public\": true, so the library will be empty.");
}

// ---- what the public entries are allowed to carry --------------------------
const keepFiles = new Set();     // exact paths under dist/books
const keepDirs = new Set();      // directories under dist/books, kept whole
const slugs = new Set();         // for matching case-drill filenames
let anyBible = false;

for (const e of publicEntries) {
  if (e.filename) {
    keepFiles.add(path.posix.normalize(e.filename));
    const base = path.posix.basename(e.filename).replace(/\.[^.]+$/, "");
    slugs.add(base);
  }
  if (e.parallelEn) {
    keepDirs.add(path.posix.normalize(e.parallelEn));
    slugs.add(String(e.parallelEn).replace(/-en$/, ""));
  }
  // Audio opts in separately — see api/catalogue.js. A public book without
  // publicAudio ships its text and nothing else.
  if (e.publicAudio === true && e.audiobook && Array.isArray(e.audiobook.chapters)) {
    for (const ch of e.audiobook.chapters) {
      const norm = path.posix.normalize(String(ch));
      keepFiles.add(norm);
      const dir = path.posix.dirname(norm);       // audio/<slug>
      if (dir && dir !== ".") keepDirs.add(dir);
      const parts = dir.split("/");
      if (parts.length > 1) slugs.add(parts[parts.length - 1]);
    }
  }
  if (e.isBible) {
    anyBible = true;
    // Scripture's English is not a parallelEn folder — it is keyed off the
    // audiobook path at runtime — so it has to be named explicitly or a public
    // Bible would ship with no English at all.
    keepDirs.add("bible-en");
    keepFiles.add("bible-headings-en.json");
  }
}

// Every directory on the way to something we keep must survive the walk.
// Without this, novel/ was deleted along with the FB2s inside it that the
// allowlist had explicitly named — the retention rule only understood kept
// directories, not the parents of kept files.
const keepAncestors = new Set();
for (const p of [...keepFiles, ...keepDirs]) {
  const parts = p.split("/");
  for (let i = 1; i < parts.length; i++) keepAncestors.add(parts.slice(0, i).join("/"));
}

// ---- walk dist/books and decide ------------------------------------------
const BOOKS = path.join(DIST, "books");
const removed = [];
const kept = [];

function rel(p) { return path.relative(BOOKS, p).split(path.sep).join("/"); }

function isKept(relPath, isDir) {
  if (keepFiles.has(relPath)) return true;
  // A directory on the path to something kept is descended into, not deleted;
  // its own children are then judged individually.
  if (isDir && keepAncestors.has(relPath)) return true;
  for (const d of keepDirs) {
    if (relPath === d || relPath.startsWith(d + "/")) return true;
  }
  // Case drills: "<slug>__chNN.json" for books, "NN-NN.json" for scripture.
  if (relPath.startsWith("exercises/")) {
    const name = path.posix.basename(relPath);
    const sep = name.indexOf("__");
    if (sep > 0) return slugs.has(name.slice(0, sep));
    if (/^\d+-\d+\.json$/.test(name)) return anyBible;
    return false;
  }
  return false;
}

function walk(dir) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    const r = rel(full);
    if (entry.isDirectory()) {
      if (isKept(r, true)) { walk(full); continue; }
      removed.push(r + "/");
      if (!DRY) fs.rmSync(full, { recursive: true, force: true });
    } else {
      if (isKept(r, false)) { kept.push(r); continue; }
      removed.push(r);
      if (!DRY) fs.rmSync(full, { force: true });
    }
  }
}

if (fs.existsSync(BOOKS)) walk(BOOKS);

// ---- the private music catalogue never ships publicly ----------------------
const privateMusic = path.join(DIST, "music", "music.json");
if (fs.existsSync(privateMusic)) {
  removed.push("../music/music.json");
  if (!DRY) fs.rmSync(privateMusic, { force: true });
}

// ---- report ---------------------------------------------------------------
const dirsRemoved = removed.filter((r) => r.endsWith("/"));
console.log("[prune] kept    " + kept.length + " files");
console.log("[prune] removed " + removed.length + " paths (" + dirsRemoved.length + " directories)");
for (const d of dirsRemoved.slice(0, 40)) console.log("          - " + d);
if (dirsRemoved.length > 40) console.log("          … and " + (dirsRemoved.length - 40) + " more");
if (DRY) console.log("[prune] DRY RUN — nothing was deleted.");
