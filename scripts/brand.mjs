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
// robots.txt: the source copy tells everything to keep out, because Говорим is
// account-gated and has no business in an index. Самовар is public, so its
// copy opens the site up and points at a sitemap — which only exists here.
const swaps = ["favicon.svg", "apple-touch-icon.png", "robots.txt", "sitemap.xml"];

const edits = [
  ["index.html", [
    ["Говорим — Russian reading practice",
     "Самовар — Russian literature with parallel English"],
    // One description string carrying both languages: there is a single URL,
    // so there is a single description, and a Russian-language search has to
    // find something Russian in it.
    ["Russian literature in the original, with an English translation beside it and a recording to listen along to. — Русская литература в оригинале, с английским переводом рядом и аудиозаписью.",
     "Read Russian literature in the original with a public-domain English translation beside it and a LibriVox recording to listen along to. Free, no account needed. — Русская классика в оригинале: параллельный английский перевод и аудиокнига LibriVox. Бесплатно, без регистрации."],
    // Говорим asks to stay out of the index; Самовар wants in.
    // The verification tag is Google Search Console's proof of ownership for
    // samovar.live — it rides along with the robots swap so it exists ONLY on
    // the public build, never on Говорим.
    ['<meta name="robots" content="noindex, nofollow" />',
     '<meta name="robots" content="index, follow" />\n    <meta name="google-site-verification" content="_2pVgU3NiXtE3VwCzRaQ7NMioWm30MYHxxIFhX98BaQ" />'],
    ["https://govorim.dev/", "https://samovar.live/"],
    ["https://govorim.dev/apple-touch-icon.png", "https://samovar.live/apple-touch-icon.png"],
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
  // sitemap.xml has no counterpart in the private build — it is added, not
  // replaced — so only the genuine swaps require an existing target.
  if (!fs.existsSync(to) && file !== "sitemap.xml") {
    console.warn("[brand] nothing to replace, skipped: dist/" + file); continue;
  }
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
