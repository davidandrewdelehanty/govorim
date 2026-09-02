#!/usr/bin/env node
// Build public/vocab/examples.json — one example sentence per headword.
//
// The source is public/vocab/blocks/, the 2,765-card frequency deck that was
// downloaded for the word-bank drill and never shipped (WORDBANK_ENABLED is
// still false). Every card already carries example_ru and example_en, which is
// exactly what the definition popup wants when the reader met a word somewhere
// with no sentence around it — a saved word, a song lyric, a search result.
//
//   node scripts/build-examples.mjs
//
// Output shape is deliberately terse, because the browser downloads it:
//   { "быть": ["Я хочу быть счастливым.", "I want to be happy.", "verb"] }
import fs from "node:fs";
import path from "node:path";

const SRC = path.join(process.cwd(), "public", "vocab", "blocks");
const OUT = path.join(process.cwd(), "public", "vocab", "examples.json");

const files = fs.readdirSync(SRC).filter((f) => /^block-\d+\.json$/.test(f)).sort();
const out = {};
let cards = 0, kept = 0;
for (const f of files) {
  const rows = JSON.parse(fs.readFileSync(path.join(SRC, f), "utf8"));
  for (const c of rows) {
    cards++;
    const ru = String(c && c.ru || "").trim().toLowerCase();
    const ex = String(c && c.example_ru || "").trim();
    if (!ru || !ex) continue;
    // The lowest rank wins: блок 1 is the commonest word, and the commonest
    // sense is the one a reader most likely met.
    if (out[ru]) continue;
    out[ru] = [ex, String(c.example_en || "").trim(), String(c.pos || "").trim()];
    kept++;
  }
}
fs.writeFileSync(OUT, JSON.stringify(out), "utf8");
const kb = Math.round(fs.statSync(OUT).size / 1024);
console.log(`${cards} cards → ${kept} headwords with an example → ${OUT} (${kb} KB)`);
