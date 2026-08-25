#!/usr/bin/env node
// Harvest блатной жаргон from ru.wiktionary into the Govorim slang glossary,
// and probe individual words against the same parser the site uses at runtime.
//
// Runs in WSL (it needs real internet, which the site's own tooling doesn't):
//
//   node tools/zhargon.mjs probe малява банковать кум
//       Fetch those words live and print exactly what /api/define would return
//       from its ru.wiktionary tier. Use this to sanity-check the parser.
//
//   node tools/zhargon.mjs list
//       Print the word list from Приложение:Уголовный жаргон and stop.
//
//   node tools/zhargon.mjs build [--limit N] [--sleep MS] [--out FILE]
//       Fetch every word in that appendix, parse each entry, and write a
//       glossary seed file (default tools/out/slang-seed.json).
//
// Then push the seed to R2 with the rclone remote already configured on this
// machine — no credentials live in this script:
//
//   RCLONE_S3_NO_CHECK_BUCKET=true \\
//     rclone copyto tools/out/slang-seed.json r2:govorim-audio/dict/slang-seed.json
//
// That env var is not optional: the R2 token is bucket-scoped, so without it
// rclone probes CreateBucket on a single-file copy and R2 answers 403.
//
// The seed file is overwritten wholesale by that copy, which is safe: entries
// curated by hand from the reader popup live in dict/slang.json instead and
// always win over the seed.

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { buildRuWiktEntry } from "../lib/ruwikt.js";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const API = "https://ru.wiktionary.org/w/api.php";
const APPENDIX = "Приложение:Уголовный жаргон";
const UA = "govorim.dev glossary harvester (personal language-learning project)";

const argv = process.argv.slice(2);
const cmd = argv[0] || "help";
const flag = (name, dflt) => {
  const i = argv.indexOf("--" + name);
  return i >= 0 && argv[i + 1] ? argv[i + 1] : dflt;
};

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function api(params) {
  const url = API + "?" + new URLSearchParams(
    Object.assign({ format: "json", formatversion: "2" }, params)
  );
  const resp = await fetch(url, { headers: { "user-agent": UA, accept: "application/json" } });
  if (!resp.ok) throw new Error("HTTP " + resp.status + " from ru.wiktionary");
  return resp.json();
}

// Pull page wikitext for up to 50 titles at a time.
async function pages(titles) {
  const data = await api({
    action: "query", prop: "revisions", rvprop: "content", rvslots: "main",
    redirects: "1", titles: titles.join("|"),
  });
  const out = new Map();
  for (const p of (data.query && data.query.pages) || []) {
    if (p.missing) continue;
    const rev = p.revisions && p.revisions[0];
    const text = rev && rev.slots && rev.slots.main && rev.slots.main.content;
    if (text) out.set(p.title, text);
  }
  // Follow the redirects the API resolved, so a listed word still finds its page.
  for (const r of (data.query && data.query.redirects) || []) {
    if (out.has(r.to)) out.set(r.from, out.get(r.to));
  }
  return out;
}

// The appendix is hand-maintained and its formatting has changed over the years:
// some entries are wikilinks, some are bold headwords, some are table rows, some
// are plain definition lists. Reading only wikilinks found 14 words on a page
// that plainly holds more, so read all four shapes — and KEEP the gloss sitting
// on the line, because most of these words have no page of their own on
// ru.wiktionary and the appendix line itself is the definition.
function wordsFromAppendix(text) {
  const found = new Map();          // key -> { word, gloss }

  const add = function (rawWord, gloss) {
    const word = String(rawWord || "").trim().replace(/^['''\u2019«"]+|['''\u2019»"]+$/g, "");
    const key = word.toLowerCase().replace(/ё/g, "е");
    if (!/^[а-яё][а-яё \-]{1,40}$/.test(key)) return;
    const clean = String(gloss || "")
      .replace(/\[\[([^\]|]*)\|([^\]]*)\]\]/g, "$2")
      .replace(/\[\[([^\]]*)\]\]/g, "$1")
      .replace(/'''/g, "")
      .replace(/\{\{[^{}]*\}\}/g, "")
      .replace(/<[^>]+>/g, "")
      .replace(/^[\s—–\-:,;]+/, "")
      .replace(/\s{2,}/g, " ")
      .trim();
    const prev = found.get(key);
    if (prev && (prev.gloss || !clean)) return;
    found.set(key, { word: word, gloss: clean });
  };

  const HEAD = "(?:\\[\\[([^\\]|#]+?)(?:\\|[^\\]]*)?\\]\\]|'''([^']+)'''|([а-яёА-ЯЁ][а-яёА-ЯЁ \\-]{1,40}?))";
  const listRe = new RegExp("^[*#:;]+\\s*" + HEAD + "\\s*(?:—|–|-|:)\\s*(.+)$");
  const rowRe  = new RegExp("^\\|\\s*" + HEAD + "\\s*\\|\\|\\s*(.+)$");
  const bareRe = new RegExp("^[*#]+\\s*(?:\\[\\[([^\\]|#]+?)(?:\\|[^\\]]*)?\\]\\]|'''([^']+)''')\\s*$");

  for (const rawLine of text.split("\n")) {
    const line = rawLine.trim();
    if (!line || /^={2,}/.test(line)) continue;

    let m = listRe.exec(line);                       // * [[слово]] — определение
    if (m) { add(m[1] || m[2] || m[3], m[4]); continue; }

    m = rowRe.exec(line);                            // | слово || определение
    if (m) { add(m[1] || m[2] || m[3], m[4]); continue; }

    m = bareRe.exec(line);                           // * [[слово]]
    if (m) { add(m[1] || m[2], ""); continue; }

    // Links inside running prose ("Смотри также [[малява]] и [[идиш]]") are NOT
    // headwords — harvesting them is how акроним, идиш and ловелас got into the
    // first seed. Only list and table lines are treated as entries.
    if (!/^[*#:;|]/.test(line)) continue;
    const re = /\[\[([^\]|#]+)(?:\|[^\]]*)?\]\]/g;
    let l;
    while ((l = re.exec(line))) {
      if (l[1].includes(":")) continue;
      add(l[1], "");
    }
  }
  return Array.from(found.values());
}

// Register labels that mark a word as belonging in a criminal-jargon glossary.
// buildRuWiktEntry renders them inline as "(jargon)", "(criminal slang)", …
const SLANGISH = ["jargon", "criminal slang", "thieves' cant", "slang", "youth slang", "low colloquial"];

function looksLikeJargon(entry) {
  const hay = ((entry.translation || "") + " " + (entry.definitionRu || "")).toLowerCase();
  return SLANGISH.some(function (label) { return hay.indexOf("(" + label) !== -1 || hay.indexOf(", " + label + ")") !== -1; });
}

function entryFor(word, text) {
  const parsed = buildRuWiktEntry(text, word, word);
  if (!parsed || !parsed.translation) return null;
  const hasEn = !!parsed.definitionRu;   // definitionRu is only set when English was found
  return {
    lemma: word,
    partOfSpeech: parsed.partOfSpeech || "",
    register: "блатной жаргон",
    translation: parsed.translation,
    definitionRu: parsed.definitionRu,
    example: parsed.example,
    exampleTranslation: "",
    source: "ru.wiktionary (CC BY-SA)",
    sourceUrl: parsed.sourceUrl,
    hasEnglish: hasEn,
  };
}

async function cmdList() {
  const got = await pages([APPENDIX]);
  const text = got.get(APPENDIX);
  if (!text) throw new Error("Could not read " + APPENDIX);
  const words = wordsFromAppendix(text);
  for (const w of words) console.log(w.word + (w.gloss ? "  —  " + w.gloss : ""));
  const withGloss = words.filter(function (w) { return w.gloss; }).length;
  console.error("\n" + words.length + " words in " + APPENDIX +
                " (" + withGloss + " with a gloss on the line)");
}

// When the extraction looks wrong, look at what the page actually says.
async function cmdRaw() {
  const lines = parseInt(flag("lines", "80"), 10);
  const got = await pages([APPENDIX]);
  const text = got.get(APPENDIX);
  if (!text) throw new Error("Could not read " + APPENDIX);
  console.log(text.split("\n").slice(0, lines).join("\n"));
  console.error("\n--- " + text.split("\n").length + " lines total; showing " + lines +
                " (--lines N for more)");
}

async function cmdProbe(words) {
  if (!words.length) return console.error("Give me words: node tools/zhargon.mjs probe малява кум");
  const got = await pages(words);
  for (const w of words) {
    const text = got.get(w) || got.get(w[0].toUpperCase() + w.slice(1));
    if (!text) { console.log("--- " + w + "\n  NO PAGE on ru.wiktionary"); continue; }
    const parsed = buildRuWiktEntry(text, w, w);
    console.log("--- " + w);
    if (!parsed) { console.log("  page exists but no Значение section could be parsed"); continue; }
    console.log("  translation : " + parsed.translation);
    if (parsed.definitionRu) console.log("  ru          : " + parsed.definitionRu);
    if (parsed.grammar) console.log("  grammar     : " + parsed.grammar);
    if (parsed.example) console.log("  example     : " + parsed.example);
  }
}

async function cmdBuild() {
  const limit = parseInt(flag("limit", "0"), 10);
  const pause = parseInt(flag("sleep", "250"), 10);
  const loose = argv.includes("--loose");
  const outPath = flag("out", path.join(HERE, "out", "slang-seed.json"));

  const got = await pages([APPENDIX]);
  const text = got.get(APPENDIX);
  if (!text) throw new Error("Could not read " + APPENDIX);
  let words = wordsFromAppendix(text);
  if (limit > 0) words = words.slice(0, limit);
  console.error(words.length + " words to fetch from " + APPENDIX);

  const glossary = {};
  let withEnglish = 0, fromAppendix = 0, dropped = 0, offTopic = 0;

  for (let i = 0; i < words.length; i += 50) {
    const batch = words.slice(i, i + 50);
    const texts = await pages(batch.map(function (w) { return w.word; }));
    for (const w of batch) {
      const key = w.word.toLowerCase().replace(/ё/g, "е");
      const t = texts.get(w.word) || texts.get(w.word[0].toUpperCase() + w.word.slice(1));
      const e = t ? entryFor(w.word, t) : null;
      if (e) {
        // A word whose entry carries no slang marker AND had no gloss on the
        // appendix line is almost certainly a stray link from the page's prose
        // — «идиш» and «акроним» arrived that way — or a same-spelling page for
        // something else entirely, like «лабух» resolving to an Austrian
        // commune. --loose keeps them.
        if (!loose && !w.gloss && !looksLikeJargon(e)) { offTopic++; continue; }
        if (e.hasEnglish) withEnglish++;
        delete e.hasEnglish;
        glossary[key] = e;
        continue;
      }
      // Most жаргон words have no entry of their own — the appendix line is
      // all there is, and it is still a real definition. Keep it rather than
      // dropping the word.
      if (w.gloss) {
        glossary[key] = {
          lemma: w.word,
          partOfSpeech: "",
          register: "блатной жаргон",
          translation: w.gloss,
          definitionRu: "",
          example: "",
          exampleTranslation: "",
          source: "ru.wiktionary, Приложение:Уголовный жаргон (CC BY-SA)",
          sourceUrl: "https://ru.wiktionary.org/wiki/" + encodeURIComponent(APPENDIX),
        };
        fromAppendix++;
        continue;
      }
      dropped++;
    }
    console.error("  " + Math.min(i + 50, words.length) + "/" + words.length +
                  "  kept " + Object.keys(glossary).length);
    if (i + 50 < words.length) await sleep(pause);
  }

  glossary._meta = {
    source: APPENDIX,
    sourceUrl: "https://ru.wiktionary.org/wiki/" + encodeURIComponent(APPENDIX),
    license: "CC BY-SA 4.0",
    built: new Date().toISOString().slice(0, 10),
    words: Object.keys(glossary).length,
  };

  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  fs.writeFileSync(outPath, JSON.stringify(glossary, null, 1), "utf8");

  console.error("\nWrote " + outPath);
  console.error("  kept              " + (Object.keys(glossary).length - 1));
  console.error("  from own entry    " + (Object.keys(glossary).length - 1 - fromAppendix));
  console.error("  from appendix line " + fromAppendix + " (no entry of their own)");
  console.error("  with English      " + withEnglish + " (the rest carry a Russian gloss)");
  console.error("  dropped           " + dropped + " (no entry and no gloss on the line)");
  console.error("  off-topic         " + offTopic + " (entry exists but reads as ordinary vocabulary; --loose keeps them)");
  console.error("\nPush it with the rclone remote already on this machine.");
  console.error("RCLONE_S3_NO_CHECK_BUCKET is required — the R2 token is bucket-scoped, so a");
  console.error("single-file copy otherwise probes CreateBucket and R2 answers 403:");
  console.error("  RCLONE_S3_NO_CHECK_BUCKET=true \\");
  console.error("    rclone copyto " + outPath + " r2:govorim-audio/dict/slang-seed.json");
}

const run = {
  list: cmdList,
  raw: cmdRaw,
  probe: () => cmdProbe(argv.slice(1).filter((a) => !a.startsWith("--"))),
  build: cmdBuild,
};
if (!run[cmd]) {
  console.error("usage: node tools/zhargon.mjs <command>");
  console.error("  probe WORD...              live-check the parser against ru.wiktionary");
  console.error("  raw [--lines N]            dump the appendix wikitext");
  console.error("  list                       words (and glosses) extracted from the appendix");
  console.error("  build [--limit N] [--sleep MS] [--out FILE] [--loose]");
  process.exit(1);
}
run[cmd]().catch((e) => { console.error("FAILED: " + e.message); process.exit(1); });
