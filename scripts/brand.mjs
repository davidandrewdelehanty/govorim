#!/usr/bin/env node
// Rebrand the static shell for the public deployment.
//
// index.html and manifest.webmanifest are not part of the JS bundle — vite
// copies public/ through untouched and only processes index.html as an entry
// point — so the SITE_NAME constant in App.jsx cannot reach them. They are
// rewritten here, after the build, against dist/ only.
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
const edits = [
  ["index.html", [
    ["Говорим — Russian Practice", "Самовар — Russian Reading"],
    ["Говорим — Russian language practice with EPUB reading and conversational tutoring.",
     "Самовар — public-domain Russian literature with parallel English translations."],
  ]],
  ["manifest.webmanifest", [
    ['"name": "Говорим"', '"name": "Самовар"'],
    ['"short_name": "Говорим"', '"short_name": "Самовар"'],
  ]],
];

let changed = 0;
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
