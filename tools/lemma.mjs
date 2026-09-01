#!/usr/bin/env node
// Probe the lemma guesser the way tools/zhargon.mjs probes the wikitext parser.
// Run it in WSL, where the machine has real internet:
//
//   node tools/lemma.mjs фраера кипежнулся банковал столе
//   node tools/lemma.mjs --file some-text.txt          # every word in a file
//
// Prints what lib/morph.js guesses and which of those guesses are real
// Викисловарь pages — the exact two steps /api/define now takes before any
// dictionary tier runs.
import { readFileSync } from "node:fs";
import { lemmaCandidates } from "../lib/morph.js";
import { existingTitles } from "../lib/ruwikt.js";

const argv = process.argv.slice(2);
let words = [];
const fileAt = argv.indexOf("--file");
if (fileAt !== -1) {
  const text = readFileSync(argv[fileAt + 1], "utf8");
  words = [...new Set((text.match(/[А-Яа-яЁё][А-Яа-яЁё-]+/g) || []).map((w) => w.toLowerCase()))];
} else {
  words = argv.filter((a) => !a.startsWith("--"));
}
if (!words.length) {
  console.error("usage: node tools/lemma.mjs <word…>  |  node tools/lemma.mjs --file <path>");
  process.exit(1);
}

let resolved = 0;
for (const w of words) {
  const guesses = lemmaCandidates(w, 12);
  let live = [];
  if (guesses.length) {
    try { live = await existingTitles(guesses, undefined); }
    catch (e) { console.log(w.padEnd(16), "ERROR", e.message); continue; }
  }
  if (live.length) resolved++;
  console.log(
    w.padEnd(16),
    (live.length ? "→ " + live.join(", ") : "→ (nothing)").padEnd(34),
    guesses.length ? "guessed: " + guesses.join(" ") : "no guess"
  );
  await new Promise((r) => setTimeout(r, 120));   // be polite to the API
}
console.log("\n" + resolved + " of " + words.length + " surface forms resolved to a real page");
