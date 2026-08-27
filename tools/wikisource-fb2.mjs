#!/usr/bin/env node
// Fetch a public-domain Russian text from ru.wikisource and emit an FB2.
//
// Runs in WSL — it needs real internet, which the Claude session does not have.
//
//   node tools/wikisource-fb2.mjs search "Медный всадник"
//       List candidate page titles so you can pick the right one.
//
//   node tools/wikisource-fb2.mjs show "Медный всадник (Пушкин)"
//       Print what would be extracted, without writing anything.
//
//   node tools/wikisource-fb2.mjs fetch "Медный всадник (Пушкин)" \
//        --out public/books/novel/pushkin-medny-vsadnik.fb2
//       Write the FB2.
//
// Why Wikisource: the text is public domain by construction and it is the same
// MediaWiki API tools/zhargon.mjs already speaks. Verse is emitted as proper
// FB2 <poem>/<stanza>/<v>, which App.jsx already renders — the same structure
// Горе от ума uses.
//
// ALWAYS eyeball `show` before `fetch`. Wikisource pages carry editorial
// apparatus (variant readings, editor's notes, indexes) that no parser can
// reliably tell from the author's text.

import fs from "node:fs";
import path from "node:path";
import { scanTemplates, templateArgs } from "../lib/ruwikt.js";

const API = "https://ru.wikisource.org/w/api.php";
const UA = "govorim.dev text fetcher (personal language-learning project)";
const argv = process.argv.slice(2);
const cmd = argv[0];
const flag = (n, d) => { const i = argv.indexOf("--" + n); return i >= 0 && argv[i + 1] ? argv[i + 1] : d; };

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function api(params, attempt = 0) {
  const url = API + "?" + new URLSearchParams(Object.assign({ format: "json", formatversion: "2" }, params));
  const r = await fetch(url, { headers: { "user-agent": UA, accept: "application/json" } });
  // Wikisource throttles a run of requests. Without this a batch reports every
  // page after the tenth as "not found", which is indistinguishable from a
  // genuinely missing page and sends you hunting for titles that were fine.
  if (r.status === 429 || r.status >= 500) {
    if (attempt >= 5) throw new Error("HTTP " + r.status + " from ru.wikisource after 6 attempts");
    const ra = parseInt(r.headers.get("retry-after") || "0", 10);
    const wait = ra > 0 ? ra * 1000 : Math.min(30000, 1500 * Math.pow(2, attempt));
    console.error("    " + r.status + " — backing off " + Math.round(wait / 1000) + "s");
    await sleep(wait);
    return api(params, attempt + 1);
  }
  if (!r.ok) throw new Error("HTTP " + r.status + " from ru.wikisource");
  return r.json();
}

async function wikitext(title) {
  const d = await api({ action: "query", prop: "revisions", rvprop: "content",
                        rvslots: "main", redirects: "1", titles: title });
  const p = (d.query && d.query.pages || [])[0];
  if (!p || p.missing) return null;
  const rev = p.revisions && p.revisions[0];
  return { title: p.title, text: rev && rev.slots && rev.slots.main && rev.slots.main.content };
}

const BOLD = "'''";

// ---- wikitext -> structured text -------------------------------------------
//
// Russian Wikisource markup as it actually appears (verified against
// "Медный всадник (Пушкин)"):
//
//   {{Отексте|...}}            multi-line header: author, source, licence
//   {{F1|title|subtitle=..|    a WRAPPER whose closing }} is the page's last
//                              line — the whole poem lives inside it, so
//                              blanket template-stripping deletes the work
//   {{poem-section|{{Sc|X}}}}  section heading
//   <p>...</p>                 prose (the preface)
//   {{indent|2}}               indentation before a verse line
//   {{indent|Отсель грозить}}  hanging indent — THE ARGUMENT IS INVISIBLE
//                              SPACING, NOT TEXT. Keeping it injects phantom
//                              words into the middle of a line.
//   {{№|5}}                    every-fifth-line numbering
//   <ref>...</ref>             footnotes, author's and editor's
//
// Blank lines separate stanzas.

const DROP_ARG = new Set(["indent", "№", "no", "nobr", "razr2"]);   // formatting only
const KEEP_ARG = new Set(["sc", "smallcaps", "razr"]);              // styled text

function inlineTemplates(s) {
  return scanTemplates(s, (inner) => {
    const args = templateArgs(inner);
    const name = args[0].trim().toLowerCase();
    if (DROP_ARG.has(name)) return "";
    if (KEEP_ARG.has(name)) return inlineTemplates(args[1] || "");
    if (name === "lang") return inlineTemplates(args[args.length - 1] || "");
    return "";
  });
}

function stripInline(s) {
  s = s.replace(/<ref[^>]*>[\s\S]*?<\/ref>/gi, "").replace(/<ref[^>]*\/>/gi, "");
  s = inlineTemplates(s);
  s = s.replace(/\[\[[^\]|]*\|([^\]]*)\]\]/g, "$1").replace(/\[\[([^\]]*)\]\]/g, "$1");
  s = s.replace(/\[https?:\/\/\S+\s+([^\]]*)\]/g, "$1");
  s = s.replace(new RegExp(BOLD + "([^']*)" + BOLD, "g"), "$1");
  s = s.replace(/''([^']*)''/g, "$1");
  s = s.replace(/<[^>]+>/g, "");
  s = s.replace(/&nbsp;?/g, " ").replace(/&[a-z]+;/g, " ");
  return s.replace(/\s+/g, " ").trim();
}

// The header template spans many lines, so it must go as a balanced unit
// before any per-line work.
function cleanPage(text) {
  let t = text.replace(/<!--[\s\S]*?-->/g, "");
  const h = t.search(/\{\{\s*[Оо]тексте/);
  if (h >= 0) {
    let depth = 0, i = h;
    while (i < t.length) {
      if (t.startsWith("{{", i)) { depth++; i += 2; }
      else if (t.startsWith("}}", i)) { depth--; i += 2; if (!depth) break; }
      else i++;
    }
    t = t.slice(0, h) + t.slice(i);
  }
  t = t.replace(/__[A-ZА-Я]+__/g, "");
  t = t.replace(/^\s*\[\[[a-z\-]{2,12}:[^\]]*\]\]\s*$/gm, "");
  t = t.replace(/\[\[(Категория|Category|Файл|File|Изображение|Image):[^\]]*\]\]/gi, "");
  return t;
}

function headerInfo(text) {
  let author = "", licence = "";
  const m = /\{\{\s*[Оо]тексте([\s\S]*?)\n\}\}/.exec(text);
  if (m) {
    for (const line of m[1].split("\n")) {
      const kv = /^\s*\|?\s*([А-ЯA-Z]+)\s*=\s*(.*)$/.exec(line);
      if (!kv) continue;
      if (kv[1] === "АВТОР" && !author) author = stripInline(kv[2]);
      if (kv[1] === "ЛИЦЕНЗИЯ" && !licence) licence = kv[2].trim();
    }
  }
  return { author, licence };
}

// -> [{ title, blocks:[{kind:"p",text} | {kind:"stanza",lines:[...]}] }]
function extract(text) {
  const sections = [];
  let cur = { title: "", blocks: [] };
  let stanza = [];
  const flush = () => { if (stanza.length) { cur.blocks.push({ kind: "stanza", lines: stanza }); stanza = []; } };
  const push = () => { flush(); if (cur.blocks.length || cur.title) sections.push(cur); };

  for (const raw of text.split("\n")) {
    const line = raw.trim();
    if (!line) { flush(); continue; }
    if (line === "}}") continue;                                  // wrapper close
    if (/^\{\{[A-Za-zА-Яа-я0-9]+\|.*\|$/.test(line)) continue;    // wrapper open {{F1|..|
    if (/^\[\[[a-z\-]{2,12}:/.test(line)) continue;               // interwiki

    const sec = /^\{\{\s*poem-section\s*\|([\s\S]*)\}\}$/.exec(line);
    if (sec) { push(); cur = { title: stripInline(sec[1]), blocks: [] }; continue; }

    if (/^<p[ >]/.test(line)) {
      flush();
      const t = stripInline(line);
      if (t) cur.blocks.push({ kind: "p", text: t });
      continue;
    }

    const v = stripInline(line);
    if (v) stanza.push(v);
  }
  push();
  return sections.filter(x => x.blocks.length);
}

// ---- FB2 -------------------------------------------------------------------

const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

function toFb2(title, author, srcUrl, sections) {
  const parts = author.replace(/\s*\(.*\)$/, "").trim().split(/\s+/);
  const last = parts.length > 1 ? parts[parts.length - 1] : author;
  const first = parts.slice(0, -1).join(" ");
  const L = [];
  L.push('<?xml version="1.0" encoding="utf-8"?>');
  L.push('<FictionBook xmlns="http://www.gribuser.ru/xml/fictionbook/2.0">');
  L.push(" <description>");
  L.push("  <title-info>");
  L.push("   <genre>poetry</genre>");
  L.push("   <author><first-name>" + esc(first) + "</first-name><last-name>" + esc(last) + "</last-name></author>");
  L.push("   <book-title>" + esc(title) + "</book-title>");
  L.push("   <lang>ru</lang>");
  L.push("  </title-info>");
  L.push("  <document-info>");
  L.push("   <program-used>tools/wikisource-fb2.mjs</program-used>");
  L.push("   <src-url>" + esc(srcUrl) + "</src-url>");
  L.push("   <version>1.0</version>");
  L.push("  </document-info>");
  L.push(" </description>");
  L.push(" <body>");
  L.push("  <title><p>" + esc(title) + "</p></title>");
  for (const sec of sections) {
    L.push("  <section>");
    if (sec.title) L.push("   <title><p>" + esc(sec.title) + "</p></title>");
    let open = false;
    for (const b of sec.blocks) {
      if (b.kind === "p") {
        if (open) { L.push("   </poem>"); open = false; }
        L.push("   <p>" + esc(b.text) + "</p>");
      } else {
        if (!open) { L.push("   <poem>"); open = true; }
        L.push("    <stanza>");
        for (const v of b.lines) L.push("     <v>" + esc(v) + "</v>");
        L.push("    </stanza>");
      }
    }
    if (open) L.push("   </poem>");
    L.push("  </section>");
  }
  L.push(" </body>");
  L.push("</FictionBook>");
  return L.join("\n") + "\n";
}

// ---- commands --------------------------------------------------------------

// When extraction looks wrong, look at the page. Guessing at the markup from
// parsed output is how the first version read a poem as prose.
async function cmdRaw(title) {
  const lines = parseInt(flag("lines", "60"), 10);
  const page = await wikitext(title);
  if (!page || !page.text) throw new Error('No such page: "' + title + '"');
  console.log(page.text.split("\n").slice(0, lines).join("\n"));
  console.error("\n--- " + page.text.split("\n").length + " lines total; showing " + lines);
}

async function cmdSearch(q) {
  const d = await api({ action: "query", list: "search", srsearch: q, srlimit: "12", srnamespace: "0" });
  for (const h of (d.query && d.query.search) || []) console.log("  " + h.title);
}

// Wikisource titles lyric poems by their FIRST LINE, so an exact title is
// often wrong for short pieces. --search resolves it instead, and always prints
// which page it landed on: picking silently would be how you end up with the
// wrong poem under the right filename.
async function resolveTitle(q) {
  const d = await api({ action: "query", list: "search", srsearch: q,
                        srlimit: "5", srnamespace: "0" });
  const hits = (d.query && d.query.search) || [];
  if (!hits.length) throw new Error('Nothing found for "' + q + '"');
  const pref = hits.find((h) => /\(Пушкин\)/.test(h.title)) || hits[0];
  console.error("resolved: " + pref.title +
                (hits.length > 1 ? "   (also: " + hits.filter(h => h !== pref)
                  .slice(0, 3).map(h => h.title).join("; ") + ")" : ""));
  return pref.title;
}

async function load(title) {
  if (argv.includes("--search")) title = await resolveTitle(title);
  const page = await wikitext(title);
  if (!page || !page.text) throw new Error('No such page: "' + title + '"');
  const info = headerInfo(page.text);
  const body = extract(cleanPage(page.text));
  return { page, info, body };
}

async function cmdShow(title) {
  const { page, info, body } = await load(title);
  const n = body.reduce((a, sec) => a + sec.blocks.reduce(
    (m, b) => m + (b.kind === "stanza" ? b.lines.length : 1), 0), 0);
  console.log("title : " + page.title);
  console.log("author: " + (info.author || "(not in the header template)"));
  console.log("licence : " + (info.licence || "(not stated)"));
  console.log("sections: " + body.map(x => x.title || "(untitled)").join(" | "));
  console.log("lines   : " + n);
  console.log("--- first 12 ---");
  const sample = body.flatMap(sec => sec.blocks.flatMap(b => b.kind === "stanza" ? b.lines : [b.text]));
  for (const l of sample.slice(0, 12)) console.log("   " + l);
  console.log("--- last 4 ---");
  for (const l of sample.slice(-4)) console.log("   " + l);
}

async function cmdFetch(title) {
  const out = flag("out", null);
  if (!out) throw new Error("--out <path> is required");
  const author = flag("author", "");
  const { page, info, body } = await load(title);
  const n = body.reduce((a, sec) => a + sec.blocks.reduce(
    (m, b) => m + (b.kind === "stanza" ? b.lines.length : 1), 0), 0);
  if (!n) throw new Error("Nothing extracted — check the page with `show` first");
  const url = "https://ru.wikisource.org/wiki/" + encodeURIComponent(page.title);
  fs.mkdirSync(path.dirname(out), { recursive: true });
  fs.writeFileSync(out, toFb2(page.title, author || info.author || "Александр Пушкин", url, body), "utf8");
  console.log("wrote " + out + "  (" + body.length + " sections, " + n + " lines)");
  console.log("source: " + url);
}

const run = { search: () => cmdSearch(argv.slice(1).join(" ")),
              raw:    () => cmdRaw(argv[1]),
              show:   () => cmdShow(argv[1]),
              fetch:  () => cmdFetch(argv[1]) };
if (!run[cmd]) {
  console.error("usage: node tools/wikisource-fb2.mjs <command>");
  console.error("  search QUERY            candidate page titles");
  console.error("  raw TITLE [--lines N]   dump the wikitext");
  console.error("  show TITLE              what would be extracted");
  console.error("  fetch TITLE --out PATH [--author NAME]");
  console.error("  ...add --search to resolve a title by search first (lyrics are");
  console.error("     titled by first line, so exact titles often miss)");
  process.exit(1);
}
run[cmd]().catch((e) => { console.error("FAILED: " + e.message); process.exit(1); });
