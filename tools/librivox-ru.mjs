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

// LibriVox files some Russian works under a LATIN transliteration — "Zapiski
// iz podpolya (Notes from the Underground)" is Записки из подполья. Comparing
// Cyrillic to Cyrillic scored that a miss and reported the catalogue as having
// nothing, which was wrong. So each record is indexed under every name it
// offers: the whole title, and each parenthesised or slash-separated alternate.
// The Cyrillic side is transliterated to Latin to meet them.
const RU2LAT = {
  а:"a",б:"b",в:"v",г:"g",д:"d",е:"e",ж:"zh",з:"z",и:"i",й:"y",к:"k",л:"l",
  м:"m",н:"n",о:"o",п:"p",р:"r",с:"s",т:"t",у:"u",ф:"f",х:"kh",ц:"ts",ч:"ch",
  ш:"sh",щ:"shch",ъ:"",ы:"y",ь:"",э:"e",ю:"yu",я:"ya",
};
function translit(s) {
  return fold(s).split("").map((c) => (c in RU2LAT ? RU2LAT[c] : c)).join("");
}

// Every name a record can be found under.
function aliases(title) {
  const parts = [title];
  const paren = title.match(/\(([^)]+)\)/g) || [];
  for (const p of paren) parts.push(p.slice(1, -1));
  parts.push(title.replace(/\([^)]*\)/g, ""));
  for (const seg of title.split("/")) parts.push(seg);
  const keys = new Set();
  for (const p of parts) {
    const f = fold(p);
    if (f) { keys.add(f); keys.add(translit(f)); }
  }
  return Array.from(keys);
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
  for (const b of ru) for (const k of aliases(b.title)) if (!index.has(k)) index.set(k, b);

  const D = JSON.parse(fs.readFileSync("private/books/index.json", "utf8"));
  // Public text, has audio, but no public-domain audio: the gap set.
  const gap = D.filter((b) => b.public === true && b.audiobook &&
                              !b.publicAudio && !b.publicAudiobook);
  console.log("  books whose audio Samovar strips: " + gap.length);
  console.log("");
  let hits = 0;
  for (const b of gap.sort((x, y) => x.title.localeCompare(y.title, "ru"))) {
    const keys = [fold(b.title), translit(b.title)];
    let found = null;
    for (const key of keys) { found = index.get(key); if (found) break; }
    if (!found) {
      // A LibriVox title often carries a subtitle or the author's name.
      for (const key of keys) {
        for (const [k, v] of index) {
          if (k.length >= 6 && (k.indexOf(key) === 0 || key.indexOf(k) === 0)) { found = v; break; }
        }
        if (found) break;
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
