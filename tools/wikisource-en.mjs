#!/usr/bin/env node
// Find English translations of the Pushkin poems on en.wikisource.
//
// Runs in WSL — it needs real internet, which the Claude session does not have.
//
//   node tools/wikisource-en.mjs survey
//       For every Pushkin work that has audio, search en.wikisource and report
//       what is there and under what licence. Touches nothing.
//
//   node tools/wikisource-en.mjs raw "The Bronze Horseman" --lines 60
//       Dump a candidate page's wikitext so its shape can be read before any
//       parser is written for it.
//
// WHY THE LICENCE COLUMN IS THE POINT
//
// Pushkin died in 1837, so every Russian text here is public domain outright.
// That says nothing about the English. A translation is a new copyrighted work
// owned by the translator, and it clears only when the TRANSLATOR's copyright
// expires. en.wikisource hosts two kinds worth having:
//
//   PD-*           the translation's own copyright has expired — usually a
//                  pre-1930 publication or a translator dead 70+ years. Free
//                  to use with no strings.
//   CC-BY-SA / *   a Wikisource volunteer translation. Usable, but share-alike:
//                  it needs a visible credit and the same licence downstream.
//                  That is a decision about the site, not a technical one, so
//                  the survey flags it rather than assuming.
//
// Anything else — no licence template, or a live copyright — is not usable and
// is reported as such.

import fs from "node:fs";
import { scanTemplates, templateArgs } from "../lib/ruwikt.js";

const API = "https://en.wikisource.org/w/api.php";
const UA = "govorim.dev text fetcher (personal language-learning project)";
const argv = process.argv.slice(2);
const cmd = argv[0];
const flag = (n, d) => { const i = argv.indexOf("--" + n); return i >= 0 && argv[i + 1] ? argv[i + 1] : d; };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const BOLD = "'".repeat(3);

async function api(params, attempt = 0) {
  const url = API + "?" + new URLSearchParams(Object.assign({ format: "json", formatversion: "2" }, params));
  const r = await fetch(url, { headers: { "user-agent": UA, accept: "application/json" } });
  if (r.status === 429 || r.status >= 500) {
    if (attempt >= 5) throw new Error("HTTP " + r.status + " from en.wikisource after 6 attempts");
    const ra = parseInt(r.headers.get("retry-after") || "0", 10);
    const wait = ra > 0 ? ra * 1000 : Math.min(30000, 1500 * Math.pow(2, attempt));
    console.error("    " + r.status + " — backing off " + Math.round(wait / 1000) + "s");
    await sleep(wait);
    return api(params, attempt + 1);
  }
  if (!r.ok) throw new Error("HTTP " + r.status + " from en.wikisource");
  return r.json();
}

async function wikitext(title) {
  const d = await api({ action: "query", prop: "revisions", rvprop: "content",
                        rvslots: "main", redirects: "1", titles: title });
  const p = (d.query && d.query.pages || [])[0];
  if (!p || p.missing) return null;
  const rev = p.revisions && p.revisions[0];
  return { title: p.title, text: (rev && rev.slots && rev.slots.main && rev.slots.main.content) || "" };
}

// ---- licence -----------------------------------------------------------------
// Read off the licence templates rather than guessing from the date: a 1930s
// translation can still be in copyright, and a modern volunteer translation is
// usable. Both facts live in the template name.

const PD = /^(pd-|public domain|no renewal|not renewed)/i;
const CC = /^(cc-|creativecommons|gfdl)/i;

function licences(text) {
  const found = new Set();
  const visit = (s) => scanTemplates(s, (inner) => {
    const args = templateArgs(inner);
    const name = args[0].trim();
    if (PD.test(name) || CC.test(name)) found.add(name);
    // {{translation licence|original=PD-old|translation=CC-BY-SA-4.0}} and the
    // {{licence}} wrappers nest the real templates one level down.
    for (let i = 1; i < args.length; i++) {
      const v = args[i].split("=").pop().trim();
      if (PD.test(v) || CC.test(v)) found.add(v);
    }
    visit(args.slice(1).join("|"));
    return "";
  });
  visit(text);
  return Array.from(found);
}

function verdict(lics) {
  if (!lics.length) return ["UNKNOWN", "no licence template on the page — check by hand"];
  const pd = lics.filter((l) => PD.test(l));
  const cc = lics.filter((l) => CC.test(l));
  // A page that carries both is the usual case: PD original, CC translation.
  // The translation's licence is the one that governs what we may ship.
  if (cc.length) return ["CC-BY-SA", "needs a credit + share-alike: " + cc.join(", ")];
  if (pd.length) return ["PD", "free to use: " + pd.join(", ")];
  return ["UNKNOWN", lics.join(", ")];
}

// Is this actually a translation of the work, or a page that merely mentions
// Pushkin? The loose version of this test accepted the Nuttall Encyclopaedia
// and an EU Council Decision. A genuine Wikisource translation page carries a
// header whose "author" is Pushkin AND names a translator; an article about
// him has neither. Both conditions, read out of the header template itself.
function headerFields(text) {
  const out = {};
  scanTemplates(text, (inner) => {
    const args = templateArgs(inner);
    if (!/^\s*(translation header|header)\s*$/i.test(args[0])) return "";
    for (let i = 1; i < args.length; i++) {
      const eq = args[i].indexOf("=");
      if (eq < 0) continue;
      const k = args[i].slice(0, eq).trim().toLowerCase();
      if (!out[k]) out[k] = args[i].slice(eq + 1).trim();
    }
    return "";
  });
  return out;
}

// Naming a translator is necessary but not sufficient: Panin's /Notes page and
// his /Narrative Poems section both name him, and neither is the poem being
// looked for. Require the page to be about the right work too — a distinctive
// word shared with the English title we searched for. "Boris Godunov" and "The
// Robber Brothers" share nothing; "I Loved You" and "I loved you" share two.
const STOPWORDS = new Set(["the","of","a","an","and","to","in","on","at","by","from","for"]);

function titleWords(t) {
  return new Set(String(t).toLowerCase().replace(/[^a-z\s]/g, " ").split(/\s+/)
    .filter((w) => w.length >= 3 && !STOPWORDS.has(w)));
}

function sameWork(wanted, pageTitle, headerTitle) {
  const want = titleWords(wanted);
  if (!want.size) return true;
  const have = new Set([...titleWords(pageTitle), ...titleWords(headerTitle)]);
  for (const w of want) if (have.has(w)) return true;
  return false;
}

function translationOf(text) {
  const h = headerFields(text);
  if (!h.author || !/pushkin/i.test(h.author)) return null;
  const tr = (h.translator || "").replace(/\[\[|\]\]/g, "").split("|").pop().trim();
  if (!tr) return null;                      // an original, or a page about him
  return { translator: tr, title: (h.title || "").trim() };
}

// ---- the works ---------------------------------------------------------------
// Russian title | slug | English titles to try, most likely first.
// Only the works that already have audio on the site — a translation with no
// recording beside it does not close a gap.

const WORKS = [
  ["Руслан и Людмила",      "pushkin-ruslan-i-lyudmila",     ["Ruslan and Ludmila", "Ruslan and Liudmila"]],
  ["Кавказский пленник",    "pushkin-kavkazsky-plennik",     ["The Prisoner of the Caucasus", "The Captive of the Caucasus"]],
  ["Гавриилиада",           "pushkin-gavriiliada",           ["The Gabriliad", "Gabrieliada"]],
  ["Братья разбойники",     "pushkin-bratya-razboyniki",     ["The Robber Brothers", "The Brothers Brigands"]],
  ["Бахчисарайский фонтан", "pushkin-bakhchisaraysky-fontan",["The Fountain of Bakhchisarai", "The Fountain of Bakhchisaray"]],
  ["Цыганы",                "pushkin-tsygany",               ["The Gypsies", "The Gipsies"]],
  ["Граф Нулин",            "pushkin-graf-nulin",            ["Count Nulin"]],
  ["Полтава",               "pushkin-poltava",               ["Poltava"]],
  ["Тазит",                 "pushkin-tazit",                 ["Tazit"]],
  ["Домик в Коломне",       "pushkin-domik-v-kolomne",       ["The Little House in Kolomna", "The Cottage in Kolomna"]],
  ["Анджело",               "pushkin-andzhelo",              ["Angelo"]],
  ["Медный всадник",        "pushkin-medny-vsadnik",         ["The Bronze Horseman"]],
  ["Монах",                 "pushkin-monakh",                ["The Monk"]],
  ["Бова",                  "pushkin-bova",                  ["Bova"]],
  ["Вадим",                 "pushkin-vadim",                 ["Vadim"]],
  ["Юдифь",                 "pushkin-yudif",                 ["Judith"]],
  ["Я вас любил",           "pushkin-ya-vas-lyubil",         ["I loved you", "I loved you once"]],
  ["Истина",                "pushkin-istina",                ["Truth"]],
  ["Красавица",             "pushkin-krasavitsa",            ["The Beauty"]],
];

async function search(q) {
  const d = await api({ action: "query", list: "search", srsearch: q + " Pushkin",
                        srlimit: "6", srnamespace: "0" });
  return ((d.query && d.query.search) || []).map((h) => h.title);
}

const pad = (v, n) => { const t = String(v); return (t.length > n - 1 ? t.slice(0, n - 2) + "\u2026" : t).padEnd(n); };

async function cmdSurvey() {
  let found = 0, none = 0;
  console.log("  " + pad("work", 24) + pad("English page", 44) + pad("licence", 10) + "translator");
  console.log("  " + "-".repeat(104));
  for (const [ru, slug, titles] of WORKS) {
    let hit = null, info = null;
    // Exact titles first: cheap and unambiguous when they work.
    for (const t of titles) {
      await sleep(2500);
      const page = await wikitext(t);
      const tr = page && page.text && translationOf(page.text);
      if (tr && sameWork(t, page.title, tr.title)) { hit = page; info = tr; break; }
    }
    if (!hit) {
      await sleep(2500);
      // Three candidates, not six: every miss costs a request and Wikisource
      // starts answering 429 well before the list is exhausted.
      for (const t of (await search(titles[0])).slice(0, 3)) {
        await sleep(2500);
        const page = await wikitext(t);
        const tr = page && page.text && translationOf(page.text);
        if (tr && sameWork(titles[0], page.title, tr.title)) { hit = page; info = tr; break; }
      }
    }
    if (!hit) {
      none++;
      console.log("  " + pad(ru, 24) + pad("-", 44) + "NOT FOUND");
      continue;
    }
    found++;
    const v = verdict(licences(hit.text));
    console.log("  " + pad(ru, 24) + pad(hit.title, 44) + pad(v[0], 10) +
                pad("tr. " + info.translator, 26) + v[1]);
  }
  console.log("");
  console.log("  found " + found + "   not found " + none);
  console.log("  PD = free to use.  CC-BY-SA = usable but needs a credit line and the");
  console.log("  same licence on the page that shows it - your call, not mine.");
}

async function cmdRaw(title) {
  const n = parseInt(flag("lines", "60"), 10);
  const page = await wikitext(title);
  if (!page) throw new Error('No such page: "' + title + '"');
  console.log(page.text.split("\n").slice(0, n).join("\n"));
  console.error("\n--- " + page.text.split("\n").length + " lines total; showing " + n);
  console.error("--- licences: " + (licences(page.text).join(", ") || "(none found)"));
}

// ---- the Panin volume --------------------------------------------------------
// "Poems by Alexander Pushkin", tr. Ivan Panin, 1888. Published in the United
// States in 1888, so public domain outright — no credit obligation, no
// share-alike. That makes it the one English source here with no strings, and
// worth handling on its own rather than through the generic survey.
//
// The catch is that Panin retitled everything into English of his own devising
// ("The Birdlet", "Death-Thoughts"), so a title alone will not tell you which
// Russian poem you are looking at. `panin` lists the volume; `panin-raw` dumps
// one poem so the Russian original can be identified before anything is built.

const PANIN = "Poems (Pushkin, Panin, 1888)";

function subpages(pageTitle, text) {
  const prefix = pageTitle + "/";
  const re = /\[\[([^\]|#]+)(?:\|([^\]]*))?\]\]/g;
  const seen = new Set(), out = [];
  let m;
  while ((m = re.exec(text))) {
    let target = m[1].trim().replace(/_/g, " ");
    if (target.charAt(0) === "/") target = pageTitle + target;
    if (target.indexOf(prefix) !== 0) continue;
    const tail = target.slice(prefix.length);
    // Panin's volume nests: the index links to sections and each section holds
    // many poems, so a deeper tail is content, not a stray cross-reference.
    if (!tail) continue;
    if (seen.has(target)) continue;
    seen.add(target);
    out.push({ title: target, label: (m[2] || tail).trim() });
  }
  return out;
}

async function cmdPanin() {
  const page = await wikitext(PANIN);
  if (!page) throw new Error("Panin volume not found at: " + PANIN);
  const lics = licences(page.text);
  console.log("volume  : " + page.title);
  console.log("licence : " + (lics.join(", ") || "(none on the index page)"));
  console.log("          published 1888 in the US — public domain regardless of template");
  const subs = subpages(page.title, page.text);
  console.log("subpages: " + subs.length);
  if (!subs.length) {
    console.log("");
    console.log("  No wikilinks to subpages on the index — its contents list is probably");
    console.log("  built by a template. Dump it and I will read the real markup:");
    console.log('    node tools/wikisource-en.mjs raw "' + PANIN + '" --lines 80');
    return;
  }
  console.log("");
  for (const s of subs) console.log("  " + s.label);
  console.log("");
  console.log("Next: dump one to see the markup and find the Russian original —");
  console.log('  node tools/wikisource-en.mjs panin-raw "' + (subs[0] ? subs[0].label : "TITLE") + '"');
}

// Accepts either the bare poem name or the full subpage title.
async function cmdPaninRaw(name) {
  if (!name) throw new Error("give a poem title");
  const title = name.indexOf(PANIN) === 0 ? name : PANIN + "/" + name;
  const n = parseInt(flag("lines", "60"), 10);
  const page = await wikitext(title);
  if (!page) throw new Error('No such page: "' + title + '"');
  console.log(page.text.split("\n").slice(0, n).join("\n"));
  console.error("\n--- " + page.text.split("\n").length + " lines total; showing " + n);
}

// ---- fetching one translation ------------------------------------------------
// Emits public/books/<slug>-en/NN.json in the {"0": "...", "1": "..."} shape the
// reader already uses: the key is the paragraph index within the Russian
// chapter. For verse that means one entry per line, so the counts on both sides
// must match exactly or the pairing silently slips by one for the whole poem.
//
// Two body shapes seen so far:
//   {{center block| line<br> line<br> ... }}   the Hewitt page
//   <poem> ... </poem>                          the usual verse wrapper
//
// NOT handled: <pages index="..." from=N to=M />. That is Proofread Page, where
// the text lives in the Page: namespace and is stitched together at render
// time - the wikitext holds a header and nothing else. Panin's whole volume is
// built that way and needs the render API instead.

function cleanEn(s) {
  s = s.replace(/<ref[^>]*>[\s\S]*?<\/ref>/gi, "").replace(/<ref[^>]*\/>/gi, "");
  s = scanTemplates(s, (inner) => {
    const args = templateArgs(inner);
    const name = args[0].trim().toLowerCase();
    // Styling wrappers keep their content; everything else is apparatus.
    if (/^(sc|smallcaps|center|italic|em|larger|smaller)$/.test(name)) return args[1] || "";
    return "";
  });
  s = s.replace(/\[\[[^\]|]*\|([^\]]*)\]\]/g, "$1").replace(/\[\[([^\]]*)\]\]/g, "$1");
  s = s.replace(new RegExp(BOLD + "([^']*)" + BOLD, "g"), "$1");
  s = s.replace(/''([^']*)''/g, "$1");
  s = s.replace(/<[^>]+>/g, "");
  s = s.replace(/&nbsp;?/g, " ").replace(/&amp;/g, "&").replace(/&[a-z]+;/g, " ");
  return s.replace(/\s+/g, " ").trim();
}

function bodyLines(text) {
  if (/<pages\s+index=/i.test(text)) {
    throw new Error("this page is a Proofread Page transclusion - its text is in " +
                    "the Page: namespace, not here; it needs the render API");
  }
  let block = null;
  const poem = /<poem>([\s\S]*?)<\/poem>/i.exec(text);
  if (poem) block = poem[1];
  if (!block) {
    // {{center block|...}} spans lines, so it has to be taken as a balanced unit.
    const at = text.search(/\{\{\s*(center block|block center|center)\s*\|/i);
    if (at >= 0) {
      let depth = 0, i = at;
      while (i < text.length) {
        if (text.startsWith("{{", i)) { depth++; i += 2; }
        else if (text.startsWith("}}", i)) { depth--; i += 2; if (!depth) break; }
        else i++;
      }
      block = templateArgs(text.slice(at + 2, i - 2)).slice(1).join("|");
    }
  }
  if (!block) throw new Error("no <poem> or {{center block}} found - dump it with `raw`");
  return block.split(/<br\s*\/?>|\n/i).map(cleanEn).filter(Boolean);
}

async function cmdFetchEn(title) {
  const slug = flag("slug", null);
  if (!slug) throw new Error("--slug <book-slug> is required");
  const page = await wikitext(title);
  if (!page) throw new Error('No such page: "' + title + '"');
  const info = translationOf(page.text);
  const lics = licences(page.text);
  const lines = bodyLines(page.text);

  const out = {};
  lines.forEach((l, i) => { out[String(i)] = l; });
  const dir = "public/books/" + slug + "-en";
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(dir + "/01.json", JSON.stringify(out), "utf8");

  console.log("wrote " + dir + "/01.json");
  console.log("lines      : " + lines.length);
  console.log("translator : " + ((info && info.translator) || "(not named)"));
  console.log("licence    : " + (lics.join(", ") || "(none found)"));
  console.log("source     : https://en.wikisource.org/wiki/" + encodeURIComponent(page.title));
  console.log("");
  console.log("Check this count against the Russian before trusting the pairing:");
  console.log("  grep -c '<v>' public/books/novel/" + slug + ".fb2");
}

const run = { survey: cmdSurvey, "fetch-en": () => cmdFetchEn(argv[1]), raw: () => cmdRaw(argv[1]),
              panin: cmdPanin, "panin-raw": () => cmdPaninRaw(argv.slice(1).filter(function(a){ return a.indexOf("--") !== 0; }).join(" ")) };
if (!run[cmd]) {
  console.error("usage: node tools/wikisource-en.mjs <command>");
  console.error("  survey                  what English translations exist, and their licences");
  console.error("  raw TITLE [--lines N]   dump one page's wikitext");
  console.error("  fetch-en TITLE --slug S the parallel English for one work");
  console.error("  panin                   list the 1888 Panin volume (public domain, no strings)");
  console.error("  panin-raw TITLE         dump one Panin poem, to identify its Russian original");
  process.exit(1);
}
run[cmd]().catch((e) => { console.error("FAILED: " + e.message); process.exit(1); });
