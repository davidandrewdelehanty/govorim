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
  // Header templates go by many names — {{Отексте}} on most pages, but
  // {{ТолстойПСС}} on the Tolstoy collected works and others elsewhere. Naming
  // them one at a time means every new author dumps its raw header into the
  // text as verse. Recognise them by SHAPE instead: a template carrying a
  // НАЗВАНИЕ or АВТОР parameter is a header, whatever it is called.
  const HEADERISH = /\|\s*(НАЗВАНИЕ|АВТОР|ЛИЦЕНЗИЯ|ДАТАСОЗДАНИЯ)\s*=/;
  for (;;) {
    const h = t.indexOf("{{");
    if (h < 0) break;
    let depth = 0, i = h;
    while (i < t.length) {
      if (t.startsWith("{{", i)) { depth++; i += 2; }
      else if (t.startsWith("}}", i)) { depth--; i += 2; if (!depth) break; }
      else i++;
    }
    if (depth !== 0) break;                       // unbalanced — leave the page alone
    const inner = t.slice(h + 2, i - 2);
    if (!HEADERISH.test(inner)) break;            // not a header; stop at the first real template
    t = t.slice(0, h) + t.slice(i);
  }
  t = t.replace(/__[A-ZА-Я]+__/g, "");
  t = t.replace(/^\s*\[\[[a-z\-]{2,12}:[^\]]*\]\]\s*$/gm, "");
  t = stripBracketLinks(t);
  return t;
}

// [[Файл:…]] captions nest other links and templates. A regex that stops at
// the first ]] cuts the caption in half — it leaves a stray ]] behind (which
// then reads as a line of verse) and, worse, can slice a {{template}} in two,
// after which brace scanning for the whole rest of the page is off by one and
// every {{poemx}} below it goes unrecognised. Count brackets instead.
const LINK_NS = /^\s*(Категория|Category|Файл|File|Изображение|Image)\s*:/i;

function stripBracketLinks(t) {
  let out = "", i = 0;
  while (i < t.length) {
    const open = t.indexOf("[[", i);
    if (open === -1) { out += t.slice(i); break; }
    if (!LINK_NS.test(t.slice(open + 2, open + 40))) {
      out += t.slice(i, open + 2); i = open + 2; continue;
    }
    out += t.slice(i, open);
    let depth = 0, j = open;
    while (j < t.length) {
      if (t.startsWith("[[", j)) { depth++; j += 2; }
      else if (t.startsWith("]]", j)) { depth--; j += 2; if (!depth) break; }
      else j++;
    }
    if (depth !== 0) { out += t.slice(open); break; }      // unbalanced — leave it
    i = j;
  }
  return out;
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

// ---- page shapes beyond the plain single-poem page --------------------------
//
// Three shapes the first version could not read, each found by dumping `raw`:
//
//   INDEX PAGE   Полтава, Кавказский пленник, Цыганы: the page is a
//                ==Содержание== list of [[Полтава (Пушкин)/Песнь первая|…]]
//                links and holds no verse at all. Followed one subpage at a
//                time, each becoming a section.
//   {{poemx|…}}  Истина and most short lyrics: title, body and date as three
//                template arguments, so the verse sits inside a balanced
//                template rather than <poem> tags. Such a page often carries
//                TWO — the lycée redaction and the canonical text — which is
//                what put "editorial apparatus" in the middle of the verse.
//   HEADINGS     Анджело, Монах: == Часть первая == / === I == with ordinary
//                <poem> blocks. Left as text those headings land in the verse
//                as lines reading "=== I ===".

const APPARATUS = /^\s*(примечани|комментари|вариант|источник|ссылк|см\.|литератур|содержание|публикаци|издани|сноск|приложени)/i;

const POEMX_MARK = "@@POEMX";
const POEMX_END = "@@ENDPOEMX@@";

// Rewrite each {{poemx|TITLE|BODY|DATE}} as a marked block so the line loop
// below can see where a poem starts and ends. The date argument is the
// editor's dating, not part of the poem, so it is dropped.
function unwrapPoemx(text) {
  let out = "", i = 0, n = 0;
  while (i < text.length) {
    const m = /\{\{\s*poemx1?\s*\|/i.exec(text.slice(i));
    if (!m) { out += text.slice(i); break; }
    const start = i + m.index;
    out += text.slice(i, start);
    let depth = 0, j = start;
    while (j < text.length) {
      if (text.startsWith("{{", j)) { depth++; j += 2; }
      else if (text.startsWith("}}", j)) { depth--; j += 2; if (!depth) break; }
      else j++;
    }
    if (depth !== 0) { out += text.slice(start); break; }   // unbalanced — leave it
    const args = templateArgs(text.slice(start + 2, j - 2));
    n++;
    const title = stripInline(args[1] || "");
    const body = String(args[2] || "").replace(/^\n+/, "").replace(/\n+$/, "");
    out += "\n" + POEMX_MARK + "|" + n + "|" + title + "@@\n" + body + "\n" + POEMX_END + "\n";
    i = j;
  }
  return { text: out, count: n };
}

const HEADING = /^(={2,6})(.+?)\1\s*$/;

// A third page shape, on the short lyrics: no {{poemx}} at all, just
//   <div class='poetry text'><div class='title'>Красавица</div><poem>…
// The title div and the composition date inside the <poem> block both read as
// lines of verse, which is where Красавица's two extra lines came from.
const TITLE_DIV = /^<div\s+class=['"][^'"]*\btitle\b[^'"]*['"]\s*>(.*?)<\/div>\s*$/i;

const MONTHS = "янв|фев|мар|апр|ма[йя]|июн|июл|авг|сен|окт|ноя|дек";

// A dateline carries a year and no words except month names — «16 мая — июнь
// 1832», «1817—1820», «<1816>». A line of verse that happens to mention a year
// has other words in it, so it is left alone.
function isDateline(raw) {
  const t = raw.replace(/^''+|''+$/g, "").replace(/^[<(\[]+|[>)\]]+$/g, "").trim();
  if (!/\b1[6-9]\d\d\b/.test(t)) return false;
  const words = t.match(/[А-Яа-яЁёA-Za-z]+/g) || [];
  const month = new RegExp("^(?:" + MONTHS + ")", "i");
  return words.every(function (w) { return month.test(w); });
}

// Which heading level are the work's own divisions at? Анджело has three
// «Часть» at level 2 and forty roman numerals at level 3: splitting on the
// numerals would give forty chapters against three audio tracks.
function chooseSplitLevel(text) {
  const counts = {};
  for (const raw of text.split("\n")) {
    const h = HEADING.exec(raw.trim());
    if (!h) continue;
    const t = stripInline(h[2]);
    if (!t || APPARATUS.test(t)) continue;
    counts[h[1].length] = (counts[h[1].length] || 0) + 1;
  }
  for (let lvl = 2; lvl <= 4; lvl++) if ((counts[lvl] || 0) >= 2) return lvl;
  return 0;
}

// -> [{ title, blocks:[{kind:"p",text} | {kind:"stanza",lines:[...]}] }]
function extract(text, opts) {
  opts = opts || {};
  const splitLevel = opts.splitLevel || 0;
  const keepPoemx = opts.keepPoemx || 0;   // 0 = keep every {{poemx}} block
  const sections = [];
  let cur = { title: "", blocks: [] };
  let stanza = [];
  let suppress = 0;        // heading level of the apparatus block being skipped
  let skipPoemx = false;
  const flush = () => { if (stanza.length) { cur.blocks.push({ kind: "stanza", lines: stanza }); stanza = []; } };
  const push = () => { flush(); if (cur.blocks.length || cur.title) sections.push(cur); };

  for (const raw of text.split("\n")) {
    const line = raw.trim();

    const px = /^@@POEMX\|(\d+)\|(.*)@@$/.exec(line);
    if (px) {
      const idx = parseInt(px[1], 10);
      skipPoemx = !!(keepPoemx && idx !== keepPoemx);
      if (!skipPoemx) { push(); cur = { title: px[2], blocks: [] }; }
      continue;
    }
    if (line === POEMX_END) { flush(); skipPoemx = false; continue; }
    if (skipPoemx) continue;

    if (!line) { flush(); continue; }

    const h = HEADING.exec(line);
    if (h) {
      const lvl = h[1].length;
      const ht = stripInline(h[2]);
      if (!ht || APPARATUS.test(ht)) { flush(); suppress = lvl; continue; }
      if (suppress && lvl > suppress) continue;
      suppress = 0;
      if (splitLevel && lvl <= splitLevel) { push(); cur = { title: ht, blocks: [] }; }
      // A deeper heading is a stanza numeral, not a chapter: it goes in as a
      // paragraph. As a <subtitle> the reader would split the audio on it.
      else { flush(); cur.blocks.push({ kind: "p", text: ht }); }
      continue;
    }
    if (suppress) continue;

    if (line === "}}") continue;                                  // wrapper close
    if (/^\{\{[A-Za-zА-Яа-я0-9]+\|.*\|$/.test(line)) continue;    // wrapper open {{F1|..|
    if (/^\[\[[a-z\-]{2,12}:/.test(line)) continue;               // interwiki

    const td = TITLE_DIV.exec(line);
    if (td) { push(); cur = { title: stripInline(td[1]), blocks: [] }; continue; }
    if (isDateline(line)) { flush(); continue; }

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

// ---- Proofread Page ----------------------------------------------------------
// A page whose wikitext is just <pages index="..." from=N to=M /> keeps its
// text in the Page: namespace and stitches it together at render time. Fetching
// the wikitext gets a header and nothing else — which is why «Детство» came
// back empty. Ask the API to RENDER it instead and read the HTML.

function decodeEntities(t) {
  return t.replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&quot;/g, '"')
          .replace(/&#(\d+);/g, (m, n) => String.fromCharCode(parseInt(n, 10)))
          .replace(/&nbsp;/g, " ").replace(/&amp;/g, "&");
}

async function renderedParagraphs(title) {
  const d = await api({ action: "parse", page: title, prop: "text",
                        redirects: "1", disablelimitreport: "1" });
  if (d.error) throw new Error("parse API: " + (d.error.info || d.error.code));
  let html = (d.parse && d.parse.text) || "";
  if (!html) return [];
  // Proofread Page marks the seam between scanned pages, and carries footnote
  // apparatus. None of it is the author's text.
  html = html.replace(/<(script|style|table)[\s\S]*?<\/\1>/gi, "");
  html = html.replace(/<sup[^>]*class="[^"]*reference[^"]*"[\s\S]*?<\/sup>/gi, "");
  html = html.replace(/<span[^>]*class="[^"]*(pagenum|pnum|ws-pagenum)[^"]*"[\s\S]*?<\/span>/gi, "");
  html = html.replace(/<div[^>]*class="[^"]*(reflist|references|noprint)[^"]*"[\s\S]*?<\/div>/gi, "");
  const out = [];
  const re = /<p[^>]*>([\s\S]*?)<\/p>/gi;
  let m;
  while ((m = re.exec(html))) {
    const t = decodeEntities(m[1].replace(/<[^>]+>/g, "")).replace(/\s+/g, " ").trim();
    if (t) out.push(t);
  }
  return out;
}

function isTransclusion(text) { return /<pages\s+index=/i.test(text); }

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

function countLines(body) {
  return body.reduce(function (a, sec) {
    return a + sec.blocks.reduce(function (m, b) {
      return m + (b.kind === "stanza" ? b.lines.length : 1);
    }, 0);
  }, 0);
}

function parsePage(text, quiet) {
  const cleaned = cleanPage(text);
  const px = unwrapPoemx(cleaned);
  let keep = 0;
  if (px.count > 1) {
    const v = String(flag("variant", "last")).toLowerCase();
    keep = v === "first" ? 1 : v === "all" ? 0 : px.count;
    if (!quiet) {
      console.error("    " + px.count + " {{poemx}} blocks on this page — using " +
                    (keep ? "#" + keep : "all of them") + "   (--variant first|last|all)");
    }
  }
  const forced = parseInt(flag("split-level", "0"), 10) || 0;
  const opts = { splitLevel: forced || chooseSplitLevel(cleaned), keepPoemx: keep };
  let body = extract(px.text, opts);
  // Choosing between two redactions must never be able to empty the page: if
  // the chosen block turns out to hold nothing, take them all instead.
  if (keep && !countLines(body)) {
    opts.keepPoemx = 0;
    body = extract(px.text, opts);
    if (!quiet) console.error("    block #" + keep + " was empty — kept all of them");
  }
  return body;
}

// An index page carries no verse, only links to its own subpages.
function subpageLinks(pageTitle, text) {
  const prefix = pageTitle + "/";
  const re = /\[\[([^\]|#]+)(?:\|([^\]]*))?\]\]/g;
  const seen = new Set(), out = [];
  let m;
  while ((m = re.exec(text))) {
    let target = m[1].trim().replace(/_/g, " ");
    // Wikisource writes these either in full or relative: [[/Посвящение|…]].
    if (target.charAt(0) === "/") target = pageTitle + target;
    if (target.indexOf(prefix) !== 0) continue;
    const tail = target.slice(prefix.length);
    if (!tail || tail.indexOf("/") >= 0) continue;
    if (APPARATUS.test(tail)) continue;
    if (seen.has(target)) continue;
    seen.add(target);
    out.push({ title: target, label: stripInline(m[2] || tail) });
  }
  return out;
}

// Some index pages link no subpages at all — «Детство (Толстой)» is a
// Proofread Page transclusion whose wikitext holds a header, one <pages/> tag
// and nothing else, though Глава I..XXVIII exist as real subpages. Where the
// names are regular, generate them rather than scrape them.
const ROMAN = [[1000,"M"],[900,"CM"],[500,"D"],[400,"CD"],[100,"C"],[90,"XC"],
               [50,"L"],[40,"XL"],[10,"X"],[9,"IX"],[5,"V"],[4,"IV"],[1,"I"]];
function roman(n) {
  let out = "";
  for (const [v, s] of ROMAN) while (n >= v) { out += s; n -= v; }
  return out;
}

function generatedSubpages(pageTitle) {
  const label = flag("subpages", null);
  const count = parseInt(flag("count", "0"), 10);
  if (!label || !count) return [];
  const arabic = argv.includes("--arabic");
  const out = [];
  for (let i = 1; i <= count; i++) {
    const num = arabic ? String(i) : roman(i);
    out.push({ title: pageTitle + "/" + label + " " + num, label: label + " " + num });
  }
  return out;
}

async function load(title) {
  if (argv.includes("--search")) title = await resolveTitle(title);
  const page = await wikitext(title);
  if (!page || !page.text) throw new Error('No such page: "' + title + '"');
  const info = headerInfo(page.text);
  let body = parsePage(page.text);
  if (!countLines(body) && isTransclusion(page.text) && !flag("subpages", null)) {
    const ps = await renderedParagraphs(page.title);
    if (ps.length) body = [{ title: "", blocks: ps.map((t) => ({ kind: "p", text: t })) }];
  }

  const gen = generatedSubpages(page.title);
  const subs = gen.length ? gen : subpageLinks(page.title, page.text);
  if (subs.length >= 2 && (gen.length || countLines(body) < 40)) {
    console.error("index page: following " + subs.length + " subpages");
    body = [];
    for (const sub of subs) {
      await sleep(1500);                     // the same pacing the batch uses
      const sp = await wikitext(sub.title);
      if (!sp || !sp.text) { console.error("    MISSING  " + sub.title); continue; }
      let secs;
      if (isTransclusion(sp.text)) {
        // Text lives in the Page: namespace; read the rendered HTML instead.
        const ps = await renderedParagraphs(sub.title);
        secs = ps.length ? [{ title: "", blocks: ps.map((t) => ({ kind: "p", text: t })) }] : [];
      } else {
        secs = parsePage(sp.text, true);
      }
      const n = countLines(secs);
      console.error("    " + sub.label + "  (" + n + " lines)");
      if (!n) continue;
      // One section per subpage: the subpage is the chapter, and its own
      // internal headings stay inside it as paragraphs.
      const blocks = [];
      for (const sec of secs) {
        if (sec.title) blocks.push({ kind: "p", text: sec.title });
        for (const b of sec.blocks) blocks.push(b);
      }
      body.push({ title: sub.label, blocks: blocks });
    }
  }
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
  // Verse lines are short; prose paragraphs are not. Printing whole paragraphs
  // dumps the entire book instead of showing what was extracted.
  const clip = (l) => (l.length > 110 ? l.slice(0, 110) + "…" : l);
  for (const l of sample.slice(0, 12)) console.log("   " + clip(l));
  console.log("--- last 4 ---");
  for (const l of sample.slice(-4)) console.log("   " + clip(l));
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

// Parse a wikitext dump saved to a file. `raw > file` then `parsefile file`
// checks a markup change offline, which is the only way to test the parser
// without hammering ru.wikisource.
async function cmdParseFile(file) {
  const text = fs.readFileSync(file, "utf8");
  const title = flag("title", path.basename(file, ".txt"));
  const body = parsePage(text);
  const subs = subpageLinks(title, text);
  console.log("sections: " + body.map((x) => x.title || "(untitled)").join(" | "));
  console.log("lines   : " + countLines(body));
  if (subs.length) console.log("subpages: " + subs.map((x) => x.label).join(" | "));
  const sample = body.flatMap((sec) => sec.blocks.flatMap((b) => b.kind === "stanza" ? b.lines : ["<p> " + b.text]));
  console.log("--- first 8 ---");
  for (const l of sample.slice(0, 8)) console.log("   " + l);
  console.log("--- last 3 ---");
  for (const l of sample.slice(-3)) console.log("   " + l);
}

async function cmdRendered(title) {
  const n = parseInt(flag("lines", "20"), 10);
  const ps = await renderedParagraphs(title);
  console.log("paragraphs: " + ps.length);
  for (const t of ps.slice(0, n)) console.log("   " + t.slice(0, 100));
}

const run = { search: () => cmdSearch(argv.slice(1).join(" ")),
              rendered: () => cmdRendered(argv[1]),
              parsefile: () => cmdParseFile(argv[1]),
              raw:    () => cmdRaw(argv[1]),
              show:   () => cmdShow(argv[1]),
              fetch:  () => cmdFetch(argv[1]) };
if (!run[cmd]) {
  console.error("usage: node tools/wikisource-fb2.mjs <command>");
  console.error("  search QUERY            candidate page titles");
  console.error("  raw TITLE [--lines N]   dump the wikitext");
  console.error("  show TITLE              what would be extracted");
  console.error("  fetch TITLE --out PATH [--author NAME]");
  console.error("  parsefile FILE [--title T]  parse a saved `raw` dump, no network");
  console.error("  --subpages LABEL --count N   build TITLE/LABEL I..N yourself, for an");
  console.error("       index page that links nothing (add --arabic for 1..N)");
  console.error("  --split-level N         force chapter splitting at heading level N");
  console.error("  --variant first|last|all  which {{poemx}} block, when a page has two");
  console.error("  ...add --search to resolve a title by search first (lyrics are");
  console.error("     titled by first line, so exact titles often miss)");
  process.exit(1);
}
run[cmd]().catch((e) => { console.error("FAILED: " + e.message); process.exit(1); });
