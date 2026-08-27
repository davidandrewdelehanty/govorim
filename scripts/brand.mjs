#!/usr/bin/env node
// Rebrand the static shell for the public deployment.
//
// index.html, manifest.webmanifest and the two icon files are not part of the
// JS bundle — vite copies public/ through untouched and only processes
// index.html as an entry point — so the SITE_NAME constant in App.jsx cannot
// reach them. They are rewritten here, after the build, against dist/ only.
//
// The source files keep the private site's branding, so this is a no-op for
// govorim and the working tree is never modified.

import fs from "node:fs";
import path from "node:path";

if (process.env.SITE_MODE !== "public") {
  console.log("[brand] SITE_MODE is not \"public\" — leaving the shell as Говорим.");
  process.exit(0);
}

const DIST = path.join(process.cwd(), "dist");
const BRAND = path.join(process.cwd(), "brand", "samovar");

// Whole-file swaps. The icons say Г for Говорим and С for Самовар, and a
// letter is not something a string substitution can do to a PNG. The Самовар
// versions live outside public/ so vite never copies them into either build —
// they only ever arrive here, over the top of the file already in dist/.
//
// favicon.svg is both the browser-tab icon and the Android "Add to Home
// screen" icon (manifest.webmanifest points at it); apple-touch-icon.png is
// the iOS one.
const swaps = ["favicon.svg", "apple-touch-icon.png"];

const edits = [
  ["index.html", [
    ["Говорим — Russian Practice", "Самовар — Russian Reading"],
    ["Говорим — Russian language practice with EPUB reading and conversational tutoring.",
     "Самовар — public-domain Russian literature with parallel English translations."],
  ]],
  ["manifest.webmanifest", [
    ['"name": "Говорим"', '"name": "Самовар"'],
    ['"short_name": "Говорим"', '"short_name": "Самовар"'],
    ['"description": "Russian language practice with EPUB reading and conversational tutoring."',
     '"description": "Public-domain Russian literature with parallel English translations."'],
  ]],
];

let changed = 0;
for (const file of swaps) {
  const from = path.join(BRAND, file);
  const to = path.join(DIST, file);
  if (!fs.existsSync(from)) { console.warn("[brand] missing source, skipped: brand/samovar/" + file); continue; }
  if (!fs.existsSync(to))   { console.warn("[brand] nothing to replace, skipped: dist/" + file); continue; }
  fs.copyFileSync(from, to);
  console.log("[brand] icon  " + file);
  changed++;
}

for (const [file, pairs] of edits) {
  const full = path.join(DIST, file);
  if (!fs.existsSync(full)) { console.warn("[brand] missing, skipped: " + file); continue; }
  let text = fs.readFileSync(full, "utf8");
  for (const [from, to] of pairs) {
    if (text.includes(from)) { text = text.split(from).join(to); changed++; }
  }
  // Anything the explicit rules missed — a stray brand mention added later.
  const before = text;
  text = text.split("Говорим").join("Самовар");
  if (text !== before) changed++;
  fs.writeFileSync(full, text, "utf8");
}

const leftovers = [];
for (const [file] of edits) {
  const full = path.join(DIST, file);
  if (fs.existsSync(full) && fs.readFileSync(full, "utf8").includes("Говорим")) leftovers.push(file);
}
console.log("[brand] rebranded the static shell for Самовар (" + changed + " substitutions).");
if (leftovers.length) {
  console.error("[brand] WARNING: Говорим still present in " + leftovers.join(", "));
}
