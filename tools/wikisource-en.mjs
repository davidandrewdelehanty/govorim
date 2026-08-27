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

import { scanTemplates, templateArgs } from "../lib/ruwikt.js";

const API = "https://en.wikisource.org/w/api.php";
const UA = "govorim.dev text fetcher (personal language-learning project)";
const argv = process.argv.slice(2);
const cmd = argv[0];
const flag = (n, d) => { const i = argv.indexOf("--" + n); return i >= 0 && argv[i + 1] ? argv[i + 1] : d; };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

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

// Is this actually a translation of the work, or an article that mentions it?
function looksLikeTranslation(text) {
  return /\{\{\s*(translation header|header)\b/i.test(text) && /pushkin/i.test(text);
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

async function cmdSurvey() {
  let found = 0, none = 0;
  for (const [ru, slug, titles] of WORKS) {
    let hit = null;
    // Exact titles first: cheap and unambiguous when they work.
    for (const t of titles) {
      await sleep(1200);
      const page = await wikitext(t);
      if (page && page.text && looksLikeTranslation(page.text)) { hit = page; break; }
    }
    if (!hit) {
      await sleep(1200);
      for (const t of await search(titles[0])) {
        await sleep(1200);
        const page = await wikitext(t);
        if (page && page.text && looksLikeTranslation(page.text)) { hit = page; break; }
      }
    }
    if (!hit) {
      none++;
      console.log("  %-24s %-40s %s", ru, "-", "NOT FOUND");
      continue;
    }
    found++;
    const v = verdict(licences(hit.text));
    console.log("  %-24s %-40s %-9s %s", ru, hit.title.slice(0, 40), v[0], v[1]);
  }
  console.log("");
  console.log("  found %d   not found %d", found, none);
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

const run = { survey: cmdSurvey, raw: () => cmdRaw(argv[1]) };
if (!run[cmd]) {
  console.error("usage: node tools/wikisource-en.mjs <command>");
  console.error("  survey                  what English translations exist, and their licences");
  console.error("  raw TITLE [--lines N]   dump one page's wikitext");
  process.exit(1);
}
run[cmd]().catch((e) => { console.error("FAILED: " + e.message); process.exit(1); });
