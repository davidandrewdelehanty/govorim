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
//   rclone copyto tools/out/slang-seed.json r2:govorim-audio/dict/slang-seed.json
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

// The appendix is a hand-maintained list and its formatting has changed over
// the years, so take the one thing that is stable: the wikilinks. Namespaced
// links (Категория:, Файл:, Приложение:) and anything non-Cyrillic are skipped.
function wordsFromAppendix(text) {
  const out = [];
  const seen = new Set();
  const re = /\[\[([^\]|#]+)(?:\|[^\]]*)?\]\]/g;
  let m;
  while ((m = re.exec(text))) {
    const raw = m[1].trim();
    if (raw.includes(":")) continue;
    const word = raw.toLowerCase();
    if (!/^[а-яё][а-яё \-]{1,40}$/.test(word)) continue;
    if (seen.has(word)) continue;
    seen.add(word);
    out.push(raw);
  }
  return out;
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
  console.log(words.join("\n"));
  console.error("\n" + words.length + " words in " + APPENDIX);
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
  const outPath = flag("out", path.join(HERE, "out", "slang-seed.json"));

  const got = await pages([APPENDIX]);
  const text = got.get(APPENDIX);
  if (!text) throw new Error("Could not read " + APPENDIX);
  let words = wordsFromAppendix(text);
  if (limit > 0) words = words.slice(0, limit);
  console.error(words.length + " words to fetch from " + APPENDIX);

  const glossary = {};
  let withEnglish = 0, noPage = 0, noParse = 0;

  for (let i = 0; i < words.length; i += 50) {
    const batch = words.slice(i, i + 50);
    const texts = await pages(batch);
    for (const w of batch) {
      const t = texts.get(w) || texts.get(w[0].toUpperCase() + w.slice(1));
      if (!t) { noPage++; continue; }
      const e = entryFor(w, t);
      if (!e) { noParse++; continue; }
      if (e.hasEnglish) withEnglish++;
      delete e.hasEnglish;
      glossary[w.toLowerCase().replace(/ё/g, "е")] = e;
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
  console.error("  kept        " + (Object.keys(glossary).length - 1));
  console.error("  with English " + withEnglish + " (the rest carry a Russian gloss)");
  console.error("  no page      " + noPage);
  console.error("  unparsable   " + noParse);
  console.error("\nPush it with the rclone remote already on this machine:");
  console.error("  rclone copyto " + outPath + " r2:govorim-audio/dict/slang-seed.json");
}

const run = { list: cmdList, probe: () => cmdProbe(argv.slice(1).filter((a) => !a.startsWith("--"))), build: cmdBuild };
if (!run[cmd]) {
  console.error("usage: node tools/zhargon.mjs <list|probe WORD...|build [--limit N] [--sleep MS] [--out FILE]>");
  process.exit(1);
}
run[cmd]().catch((e) => { console.error("FAILED: " + e.message); process.exit(1); });
