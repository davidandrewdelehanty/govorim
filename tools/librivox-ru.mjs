#!/usr/bin/env node
// What does LibriVox actually have in Russian, and does any of it match the
// books whose audio Samovar has to strip?
//
// Runs in WSL — it needs real internet.
//
//   node tools/librivox-ru.mjs list
//       Every completed Russian recording LibriVox holds. Cached after the
//       first run.
//
//   node tools/librivox-ru.mjs match
//       Cross-reference that catalogue against the books in private/books/
//       index.json that are public but whose audio the public build drops —
//       i.e. exactly the set a public-domain recording would rescue.
//
// LibriVox's API has no language filter, so `list` pages the whole catalogue
// once and keeps the Russian rows. That is ~20k records, hence the cache.

import fs from "node:fs";
import path from "node:path";

const API = "https://librivox.org/api/feed/audiobooks";
const UA = "govorim.dev catalogue check (personal language-learning project)";
const CACHE = ".cache/librivox-ru.json";
const argv = process.argv.slice(2);
const cmd = argv[0];
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function page(offset, limit) {
  const url = API + "/?format=json&offset=" + offset + "&limit=" + limit;
  const r = await fetch(url, { headers: { "user-agent": UA, accept: "application/json" } });
  if (r.status === 429 || r.status >= 500) {
    await sleep(4000);
    return page(offset, limit);
  }
  // LibriVox answers 404 when the offset runs past the end of the catalogue
  // rather than returning an empty list, so 404 IS the end of pagination — not
  // a failure. Treating it as one threw away a completed 22,000-record scan.
  if (r.status === 404) return [];
  if (!r.ok) throw new Error("HTTP " + r.status + " from LibriVox");
  const d = await r.json();
  return (d && d.books) || [];
}

async function russianCatalogue() {
  if (fs.existsSync(CACHE)) {
    console.error("using cached " + CACHE);
    return JSON.parse(fs.readFileSync(CACHE, "utf8"));
  }
  const LIMIT = 500;
  const out = [];
  for (let off = 0; ; off += LIMIT) {
    const books = await page(off, LIMIT);
    if (!books.length) break;
    for (const b of books) {
      if (String(b.language || "").toLowerCase() !== "russian") continue;
      out.push({
        id: b.id,
        title: String(b.title || "").trim(),
        author: ((b.authors || [])[0] || {}).last_name || "",
        url: b.url_librivox || "",
      });
    }
    process.stderr.write("\r  scanned " + (off + books.length) + " records, " + out.length + " Russian");
    await sleep(300);
  }
  process.stderr.write("\n");
  fs.mkdirSync(path.dirname(CACHE), { recursive: true });
  fs.writeFileSync(CACHE, JSON.stringify(out, null, 1), "utf8");
  console.error("cached " + out.length + " Russian titles to " + CACHE);
  return out;
}

// Cyrillic titles differ by case, ё, and punctuation between sources, so
// compare on a folded key rather than the raw string.
function fold(s) {
  return String(s).toLowerCase().replace(/ё/g, "е")
    .replace(/[^\p{L}\p{N}]+/gu, " ").trim();
}

async function cmdList() {
  const ru = await russianCatalogue();
  ru.sort((a, b) => a.title.localeCompare(b.title, "ru"));
  for (const b of ru) console.log("  " + b.title + (b.author ? "  — " + b.author : ""));
  console.log("\n  " + ru.length + " Russian recordings");
}

async function cmdMatch() {
  const ru = await russianCatalogue();
  const index = new Map();
  for (const b of ru) index.set(fold(b.title), b);

  const D = JSON.parse(fs.readFileSync("private/books/index.json", "utf8"));
  // Public text, has audio, but no public-domain audio: the gap set.
  const gap = D.filter((b) => b.public === true && b.audiobook &&
                              !b.publicAudio && !b.publicAudiobook);
  console.log("  books whose audio Samovar strips: " + gap.length);
  console.log("");
  let hits = 0;
  for (const b of gap.sort((x, y) => x.title.localeCompare(y.title, "ru"))) {
    const key = fold(b.title);
    let found = index.get(key);
    if (!found) {
      // A LibriVox title often carries a subtitle or the author's name.
      for (const [k, v] of index) {
        if (k.indexOf(key) === 0 || key.indexOf(k) === 0) { found = v; break; }
      }
    }
    if (found) { hits++; console.log("  HIT   " + b.title.padEnd(28) + found.url); }
    else console.log("  --    " + b.title);
  }
  console.log("");
  console.log("  " + hits + " of " + gap.length + " could get a public-domain recording");
}

const run = { list: cmdList, match: cmdMatch };
if (!run[cmd]) {
  console.error("usage: node tools/librivox-ru.mjs <list|match>");
  process.exit(1);
}
run[cmd]().catch((e) => { console.error("FAILED: " + e.message); process.exit(1); });
