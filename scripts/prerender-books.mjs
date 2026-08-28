#!/usr/bin/env node
// Prerender one real HTML page per public book, for search engines.
//
// samovar.live is a single-page app, which to a crawler is a single PAGE: one
// URL, one title, one description, for a site that actually holds ~60 works.
// Nobody searching for a specific book can land on it. This script gives every
// public book a URL of its own — /book/<slug>/ — as a static file in dist/,
// so Vercel serves it without any server rendering:
//
//   dist/book/belye-nochi/index.html
//
// Each page is the branded app shell with its <head> rewritten for that book
// (title, description, canonical, Open Graph, JSON-LD) and the opening of the
// actual Russian text placed inside #root, where a crawler reads it and React
// replaces it the moment the app mounts. The app half of the feature lives in
// App.jsx: on boot it looks at location.pathname and opens the matching book.
//
// Also writes the real sitemap.xml (home + every book page), replacing the
// one-URL placeholder brand.mjs copies in.
//
// Runs after brand.mjs and prune-public.mjs — public builds only.

import fs from "node:fs";
import path from "node:path";

if (process.env.SITE_MODE !== "public") {
  console.log("[prerender] SITE_MODE is not \"public\" — skipped.");
  process.exit(0);
}

const ROOT = process.cwd();
const DIST = path.join(ROOT, "dist");
const ORIGIN = "https://samovar.live";
const manifest = JSON.parse(fs.readFileSync(path.join(ROOT, "private", "books", "index.json"), "utf8"));
const shell = fs.readFileSync(path.join(DIST, "index.html"), "utf8");

const esc = (s) => String(s || "")
  .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

// The opening of the book, straight from the FB2: strip binaries, take the
// first body, drop titles/epigraphs, and keep the first few real paragraphs.
function excerpt(fb2Path) {
  let src;
  try { src = fs.readFileSync(fb2Path, "utf8"); } catch { return []; }
  src = src.replace(/<binary[\s\S]*?<\/binary>/g, "");
  const body = /<body(?:\s[^>]*)?>([\s\S]*?)<\/body>/.exec(src);
  if (!body) return [];
  let text = body[1]
    .replace(/<title>[\s\S]*?<\/title>/g, "")
    .replace(/<epigraph>[\s\S]*?<\/epigraph>/g, "");
  const out = [];
  const clean = (raw) => raw.replace(/<[^>]+>/g, "")
    .replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"').replace(/&#(\d+);/g, (_, n) => String.fromCharCode(n))
    .replace(/\s+/g, " ").trim();
  const collect = (re) => {
    let m, total = 0;
    while ((m = re.exec(text)) && out.length < 6 && total < 900) {
      const p = clean(m[1]);
      // Wiki-template leftovers ({{эпиграф|...}}) are markup, not the book.
      if (p.length < 2 || p.includes("{{") || p.includes("}}")) continue;
      out.push(p);
      total += p.length;
    }
  };
  collect(/<p(?:\s[^>]*)?>([\s\S]*?)<\/p>/g);
  // A few FB2s carry their prose in <v> verse lines inside <poem> blocks
  // (and every poem does) — fall back to those when <p> found nothing.
  if (!out.length) collect(/<v(?:\s[^>]*)?>([\s\S]*?)<\/v>/g);
  return out;
}

// "English by Constance Garnett (1912), public domain. …" → "Constance Garnett"
function translatorOf(note) {
  const m = /English by ([^(,.]+?)(?:\s*\(|,|\.)/.exec(note || "");
  return m ? m[1].trim() : null;
}

const CATEGORY_EN = {
  "Novels": "novel", "Novellas": "novella", "Short Stories": "short story",
  "Plays": "play", "Poetry": "poem", "Religious Texts": "religious text",
  "Speeches by Soviet Leaders": "speech", "Spectacle": "radio play",
};

function headSwap(html, re, replacement, what, slug) {
  if (!re.test(html)) { console.warn(`[prerender] ${slug}: could not rewrite ${what}`); return html; }
  return html.replace(re, replacement);
}

const books = manifest.filter((e) => e && e.public === true && e.slug);
const urls = [ORIGIN + "/"];
let written = 0;

for (const book of books) {
  const slug = book.slug;
  const url = `${ORIGIN}/book/${slug}/`;
  const translator = translatorOf(book.translationNote);
  const hasEn = !!book.parallelEn;
  const hasAudio = !!(book.publicAudiobook || (book.audiobook && book.publicAudio === true));
  const kind = CATEGORY_EN[book.category] || "work";

  const title = `«${book.title}» — ${book.author || ""} · read in Russian${hasEn ? " with English translation" : ""} | Самовар`;
  const descEn =
    `Read ${book.title} by ${book.author || "?"} in the original Russian, free` +
    (hasEn ? `, with ${translator ? translator + "’s" : "a"} public-domain English translation beside the text` : "") +
    (hasAudio ? ", and an audiobook recording to listen along to" : "") +
    ". Tap any word for a dictionary definition.";
  const descRu =
    `«${book.title}» — ${book.author || ""}: читать онлайн бесплатно в оригинале` +
    (hasEn ? ", с параллельным английским переводом" : "") +
    (hasAudio ? " и аудиокнигой" : "") + ".";
  const desc = descEn + " — " + descRu;
  const keywords =
    `${book.title}, ${book.author || ""}, read in Russian, Russian ${kind}, ` +
    (hasEn ? `parallel text, English translation${translator ? ", " + translator : ""}, ` : "") +
    (hasAudio ? "Russian audiobook, " : "") +
    `${book.title} читать онлайн, ${book.title} оригинал` + (hasEn ? ", параллельный перевод" : "");

  let html = shell;
  html = headSwap(html, /<title>[^<]*<\/title>/, `<title>${esc(title)}</title>`, "title", slug);
  html = headSwap(html, /(<meta name="description" content=")[^"]*(")/, `$1${esc(desc)}$2`, "description", slug);
  html = headSwap(html, /(<meta name="keywords" content=")[^"]*(")/, `$1${esc(keywords)}$2`, "keywords", slug);
  html = headSwap(html, /(<link rel="canonical" href=")[^"]*(")/, `$1${url}$2`, "canonical", slug);
  html = headSwap(html, /(<meta property="og:type" content=")[^"]*(")/, `$1book$2`, "og:type", slug);
  html = headSwap(html, /(<meta property="og:title" content=")[^"]*(")/, `$1${esc(title)}$2`, "og:title", slug);
  html = headSwap(html, /(<meta property="og:description" content=")[^"]*(")/, `$1${esc(desc)}$2`, "og:description", slug);
  html = headSwap(html, /(<meta property="og:url" content=")[^"]*(")/, `$1${url}$2`, "og:url", slug);
  html = headSwap(html, /(<meta name="twitter:title" content=")[^"]*(")/, `$1${esc(title)}$2`, "twitter:title", slug);
  html = headSwap(html, /(<meta name="twitter:description" content=")[^"]*(")/, `$1${esc(desc)}$2`, "twitter:description", slug);

  const ld = {
    "@context": "https://schema.org",
    "@type": "Book",
    name: book.title,
    author: { "@type": "Person", name: book.author || "" },
    inLanguage: "ru",
    genre: book.category || "",
    url,
    isAccessibleForFree: true,
  };
  if (hasEn && translator) ld.translator = { "@type": "Person", name: translator };
  html = html.replace("</head>",
    `  <script type="application/ld+json">${JSON.stringify(ld)}</script>\n  </head>`);

  // Visible page content: real for a crawler, replaced by React for a person.
  const paras = excerpt(path.join(ROOT, "public", "books", book.filename));
  const content =
    `<div class="nojs">` +
    `<h1 lang="ru">${esc(book.title)}</h1>` +
    `<p lang="ru">${esc(book.author || "")}</p>` +
    `<p lang="en">Read this Russian ${esc(kind)} in the original on Самовар — free, no account needed` +
    (hasEn ? `, with ${translator ? esc(translator) + "’s" : "an"} English translation beside the text` : "") +
    (hasAudio ? ", and an audiobook to listen along to" : "") + `.</p>` +
    (book.translationNote ? `<p lang="en">${esc(book.translationNote)}</p>` : "") +
    (paras.length ? `<h2 lang="ru">Начало</h2>` + paras.map((p) => `<p lang="ru">${esc(p)}</p>`).join("") : "") +
    `<p><a href="/">Самовар — the whole library / вся библиотека</a></p>` +
    `</div>`;
  html = headSwap(html, /<div id="root"><\/div>/, `<div id="root">${content}</div>`, "#root", slug);

  const dir = path.join(DIST, "book", slug);
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, "index.html"), html, "utf8");
  urls.push(url);
  written++;
}

// The home page gets its WebSite JSON-LD too.
const homePath = path.join(DIST, "index.html");
let home = fs.readFileSync(homePath, "utf8");
if (!home.includes('"@type":"WebSite"')) {
  const siteLd = {
    "@context": "https://schema.org", "@type": "WebSite",
    name: "Самовар", alternateName: "Samovar",
    url: ORIGIN + "/", inLanguage: ["ru", "en"],
    description: "Russian literature in the original with parallel English translations and audiobooks.",
  };
  home = home.replace("</head>",
    `  <script type="application/ld+json">${JSON.stringify(siteLd)}</script>\n  </head>`);
  fs.writeFileSync(homePath, home, "utf8");
}

const today = new Date().toISOString().slice(0, 10);
const sitemap =
  `<?xml version="1.0" encoding="UTF-8"?>\n` +
  `<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n` +
  urls.map((u) => `  <url><loc>${u}</loc><lastmod>${today}</lastmod></url>`).join("\n") +
  `\n</urlset>\n`;
fs.writeFileSync(path.join(DIST, "sitemap.xml"), sitemap, "utf8");

console.log(`[prerender] ${written} book pages + sitemap (${urls.length} URLs).`);
