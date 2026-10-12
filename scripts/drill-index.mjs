#!/usr/bin/env node
// Index of every case drill the build ships, for the Case drills tab.
//
// Drills live one file per chapter in books/exercises/, named after the book
// and chapter they came from. The tab draws questions at random from all of
// them, so it needs one list of what exists and which book each file belongs
// to. That list is written here, after prune-public has removed whatever this
// deployment must not ship, so it only ever names files that are really there
// and books this site may show. Restricted books are left out on both sites.
//
//   { books: [{ f, t, a }], d: [[bookIndex, chapterIndex, questions, key?]] }
//
// `key` is given only when the file is not the usual "<slug>__ch<N>".

import fs from "node:fs";
import path from "node:path";

const ROOT = process.cwd();
const DIST = path.join(ROOT, "dist", "books", "exercises");
const PUBLIC = process.env.SITE_MODE === "public";

if (!fs.existsSync(DIST)) {
  console.log("[drill-index] no dist/books/exercises — nothing to index.");
  process.exit(0);
}
const manifest = JSON.parse(fs.readFileSync(path.join(ROOT, "private", "books", "index.json"), "utf8"));

const slugOf = (fn) => path.posix.basename(fn).replace(/\.[^.]+$/, "").replace(/[^A-Za-z0-9_-]/g, "_");
// The audio-path key App.jsx falls back to for older drill sets.
const audioKey = (cp) => {
  cp = String(cp || "");
  if (!cp) return "";
  const bm = cp.match(/bible-nrp\/(\d+-\d+)\.json/);
  if (bm) return bm[1];
  let s = cp.split("?")[0];
  if (s.indexOf("audio/") !== -1) s = s.split("audio/").pop();
  return s.replace(/\.json$/, "").replace(/\//g, "__");
};

const books = [];
const bookIdx = new Map();      // filename -> index in books
const bySlug = new Map();       // slug -> [entry]
const byAudio = new Map();      // audio key -> [entry, cidx]
for (const e of manifest) {
  if (!e || !e.filename || e.restricted) continue;
  if (PUBLIC && e.public !== true) continue;
  const s = slugOf(e.filename);
  if (!bySlug.has(s)) bySlug.set(s, []);
  bySlug.get(s).push(e);
  const chs = e.audiobook && e.audiobook.chapters;
  if (Array.isArray(chs)) chs.forEach((cp, i) => {
    const k = audioKey(cp);
    if (k && !byAudio.has(k)) byAudio.set(k, [e, i]);
  });
}
const idxOf = (e) => {
  if (!bookIdx.has(e.filename)) {
    bookIdx.set(e.filename, books.length);
    books.push({ f: e.filename, t: e.title || "", a: e.author || "" });
  }
  return bookIdx.get(e.filename);
};

const d = [];
let skipped = 0;
for (const name of fs.readdirSync(DIST)) {
  if (!name.endsWith(".json") || name.startsWith("_")) continue;
  const key = name.slice(0, -5);
  let entry = null, cidx = -1, std = false;
  const m = key.match(/^(.*)__ch(\d+)$/);
  if (m && bySlug.has(m[1])) {
    const list = bySlug.get(m[1]);
    // Two Cyrillic titles can share a slug; such a file cannot be placed.
    if (list.length === 1) { entry = list[0]; cidx = +m[2]; std = true; }
  }
  if (!entry && byAudio.has(key)) [entry, cidx] = byAudio.get(key);
  if (!entry) { skipped++; continue; }
  let n = 0;
  try {
    const j = JSON.parse(fs.readFileSync(path.join(DIST, name), "utf8"));
    n = ((j && j.cases) || []).filter((c) => c && c.sentence && /___/.test(c.sentence) && c.options && c.correct).length;
  } catch (e) { n = 0; }
  if (!n) continue;
  const row = [idxOf(entry), cidx, n];
  if (!std) row.push(key);
  d.push(row);
}
fs.writeFileSync(path.join(DIST, "_index.json"), JSON.stringify({ books, d }));
console.log(`[drill-index] ${d.length} drill files from ${books.length} books indexed (${skipped} unplaced).`);
