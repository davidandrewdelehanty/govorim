#!/usr/bin/env node
// Pull a public-domain English translation out of an archive.org scan and emit
// the parallel-text JSON the reader consumes.
//
// Runs in WSL — it needs real internet.
//
//   node tools/archive-en.mjs survey translationsfrom00pushuoft
//       Download the OCR text (cached) and print the headings it can see, so
//       the boundaries of each work can be chosen by eye.
//
//   node tools/archive-en.mjs slice translationsfrom00pushuoft \
//        --from "THE BRONZE CAVALIER" --to "THE STATUE GUEST" --lines 30
//       Preview what those boundaries actually capture. ALWAYS do this first.
//
//   node tools/archive-en.mjs fetch translationsfrom00pushuoft \
//        --from "THE BRONZE CAVALIER" --to "THE STATUE GUEST" \
//        --slug pushkin-medny-vsadnik
//       Write public/books/<slug>-en/NN.json, one file per Russian chapter.
//
// ON ALIGNMENT
//
// A verse translator does not preserve line counts — Turner expands some of
// Pushkin's lines and compresses others, so 493 Russian lines might come out as
// 520 English ones. Pairing them index-for-index would drift further out of
// step with every stanza and be wrong for the whole poem while still looking
// like it works.
//
// So the English is BUCKETED instead: each Russian chapter gets the matching
// proportional span of English, and within it each Russian line gets the
// English lines that fall in its share. Drift is therefore local and small
// rather than accumulating, and it re-syncs at every chapter boundary. It is
// still approximate, which is why the catalogue entry carries a note saying so.
//
// A bucket that comes out empty is left out of the JSON rather than filled with
// a repeat of its neighbour: a blank cell reads as "this line is covered by the
// one above", where a duplicate reads as a bug.

import fs from "node:fs";
import path from "node:path";

const argv = process.argv.slice(2);
const cmd = argv[0];
const id = argv[1];
const flag = (n, d) => { const i = argv.indexOf("--" + n); return i >= 0 && argv[i + 1] ? argv[i + 1] : d; };
const CACHE = ".cache/archive";

async function ocrText(archiveId) {
  const file = path.join(CACHE, archiveId + ".txt");
  if (fs.existsSync(file)) {
    console.error("using cached " + file);
    return fs.readFileSync(file, "utf8");
  }
  const url = "https://archive.org/download/" + archiveId + "/" + archiveId + "_djvu.txt";
  console.error("downloading " + url);
  const r = await fetch(url, { headers: { "user-agent": "govorim.dev text fetcher" } });
  if (!r.ok) throw new Error("HTTP " + r.status + " from archive.org — check the id");
  const text = await r.text();
  fs.mkdirSync(CACHE, { recursive: true });
  fs.writeFileSync(file, text, "utf8");
  console.error("cached to " + file + "  (" + Math.round(text.length / 1024) + " KB)");
  return text;
}

// ---- OCR cleanup -------------------------------------------------------------
// What this scan actually contains, from its own errata page onward: running
// headers, bare page numbers, footnote markers, and broken words. Only the
// mechanical noise is removed here — a wrong letter inside a word cannot be
// fixed without the original, and guessing at it would be worse than leaving it.

const NOISE = [
  /^\s*\d+\s*$/,                      // bare page number
  /^\s*[IVXLC]+\*?\s*$/,              // canto numeral alone on a line
  /^\s*[A-Z][A-Z\s.'-]{6,}\s*\d*\s*$/, // running header in caps
  /^\s*\d+\s*\*+\s*$/,                // signature marks like "1*"
];

function isNoise(line) {
  const t = line.trim();
  if (!t) return true;
  return NOISE.some((re) => re.test(t));
}

function cleanLine(s) {
  // The OCR doubles spaces between every word on this scan.
  return s.replace(/\s+/g, " ").replace(/\s+([,.;:!?])/g, "$1").trim();
}

function bodyLines(text, from, to) {
  const lines = text.split("\n");
  const find = (needle, startAt) => {
    if (!needle) return -1;
    const want = needle.toUpperCase().replace(/\s+/g, "");
    for (let i = startAt; i < lines.length; i++) {
      if (lines[i].toUpperCase().replace(/\s+/g, "").indexOf(want) === 0) return i;
    }
    return -1;
  };
  // The contents page names every work too, so the FIRST match is the table of
  // contents and the second is the work itself. Skip past the front matter.
  let a = find(from, 0);
  if (a >= 0) { const again = find(from, a + 1); if (again > 0) a = again; }
  if (a < 0) throw new Error('--from "' + from + '" not found');
  let b = to ? find(to, a + 1) : -1;
  if (b < 0) b = lines.length;
  return lines.slice(a + 1, b).filter((l) => !isNoise(l)).map(cleanLine).filter(Boolean);
}

// ---- the Russian side --------------------------------------------------------
// Chapter and paragraph counts have to come from the FB2 itself, because the
// bucketing divides the English by exactly those numbers.

function russianShape(slug) {
  const file = "public/books/novel/" + slug + ".fb2";
  const xml = fs.readFileSync(file, "utf8");
  const body = xml.slice(xml.indexOf("<body>"));
  const secs = body.split(/<section>/).slice(1);
  const counts = secs.map((s) => (s.match(/<v>|<p>/g) || []).length)
                     .filter((n) => n > 0);
  if (!counts.length) throw new Error("no sections found in " + file);
  return counts;
}

// ---- commands ----------------------------------------------------------------

async function cmdSurvey() {
  const text = await ocrText(id);
  const lines = text.split("\n");
  console.log("total lines: " + lines.length);
  console.log("");
  console.log("Headings the scan shows (all-caps lines, 4+ chars):");
  let shown = 0;
  for (let i = 0; i < lines.length && shown < 80; i++) {
    const t = lines[i].trim();
    if (/^[A-Z][A-Z\s.'-]{3,}$/.test(t) && t.replace(/\s/g, "").length >= 4) {
      console.log("  " + String(i).padStart(6) + "  " + t);
      shown++;
    }
  }
  console.log("");
  console.log("Pick boundaries from these, then preview with `slice` before `fetch`.");
}

async function cmdSlice() {
  const text = await ocrText(id);
  const n = parseInt(flag("lines", "30"), 10);
  const lines = bodyLines(text, flag("from", null), flag("to", null));
  console.log("captured " + lines.length + " lines");
  console.log("--- first " + n + " ---");
  for (const l of lines.slice(0, n)) console.log("   " + l);
  console.log("--- last 5 ---");
  for (const l of lines.slice(-5)) console.log("   " + l);
}

async function cmdFetch() {
  const slug = flag("slug", null);
  if (!slug) throw new Error("--slug <book-slug> is required");
  const text = await ocrText(id);
  const en = bodyLines(text, flag("from", null), flag("to", null));
  const ru = russianShape(slug);
  const ruTotal = ru.reduce((a, b) => a + b, 0);

  console.log("English lines : " + en.length);
  console.log("Russian lines : " + ruTotal + "  in " + ru.length + " chapter(s): " + ru.join(", "));
  console.log("ratio         : " + (en.length / ruTotal).toFixed(2) + " English lines per Russian line");
  console.log("                (a ratio far from 1.0 means the boundaries are wrong)");
  console.log("");

  // A translator often skips what is not verse. Turner opens at Pushkin's
  // Вступление, leaving the prose Предисловие — chapter 1 of the Russian —
  // with no counterpart. Spread across every chapter regardless, that one
  // absent section shifts the whole poem out of step, so the English can be
  // told which chapter it really starts at.
  const first = Math.max(1, parseInt(flag("from-chapter", "1"), 10)) - 1;
  if (first > 0) {
    console.log("skipping chapters 1-" + first + " (no English for them)");
    console.log("");
  }
  const paired = ru.slice(first);
  const pairedTotal = paired.reduce((a, b) => a + b, 0);

  const dir = "public/books/" + slug + "-en";
  fs.mkdirSync(dir, { recursive: true });
  let cursor = 0;
  paired.forEach((paras, pi) => {
    const ci = pi + first;
    // This chapter's share of the English, proportional to its share of the
    // Russian — so a chapter boundary always re-syncs the two sides.
    const share = Math.round(en.length * (paras / pairedTotal));
    const slice = en.slice(cursor, ci === ru.length - 1 ? en.length : cursor + share);
    cursor += slice.length;
    const out = {};
    for (let i = 0; i < paras; i++) {
      const a = Math.floor(i * slice.length / paras);
      const b = Math.floor((i + 1) * slice.length / paras);
      const chunk = slice.slice(a, b).join(" ");
      if (chunk) out[String(i)] = chunk;      // empty bucket: leave the cell blank
    }
    const name = String(ci + 1).padStart(2, "0") + ".json";
    fs.writeFileSync(path.join(dir, name), JSON.stringify(out), "utf8");
    console.log("  " + name + "  " + paras + " Russian lines <- " + slice.length +
                " English lines, " + Object.keys(out).length + " filled");
  });
  console.log("");
  console.log("wrote " + dir + "/");
  console.log("Read a few lines of each before trusting it — OCR noise survives cleanup.");
}

const run = { survey: cmdSurvey, slice: cmdSlice, fetch: cmdFetch };
if (!run[cmd] || !id) {
  console.error("usage: node tools/archive-en.mjs <command> <archive-id> [options]");
  console.error("  survey ID                       headings in the scan");
  console.error("  slice  ID --from S [--to S]     preview a range");
  console.error("  fetch  ID --from S [--to S] --slug SLUG [--from-chapter N]");
  process.exit(1);
}
run[cmd]().catch((e) => { console.error("FAILED: " + e.message); process.exit(1); });
