// Word form → lemma, from the pymorphy3 table (tools/lemmas/build_lemmas.py).
//
// pymorphy3 analyses Russian against the OpenCorpora dictionary, so it knows
// the forms no ending rule can reach — людьми → человек, шёл → идти, лучше →
// хороший — and says which part of speech each reading is. It runs offline,
// over every word the library holds, and the answers sit in lemmas/ beside
// this function (vercel.json includes them). One small shard per lookup, read
// from disk and kept warm.
//
// Returns { known, readings: [{ lemma, pos }] } or null. `known` false means
// pymorphy3 guessed from the ending (the word is not in its dictionary): treat
// the lemma as a candidate to verify, not as a fact.
import fs from "fs";
import path from "path";

const ALPH = "абвгдеёжзийклмнопрстуфхцчшщъыьэюя";
const CODE = "0123456789abcdefghijklmnopqrstuvw";
const DIR = path.join(process.cwd(), "lemmas");
const cache = new Map();          // shard → object, most recent last
let split = null;

function code(c) {
  const i = ALPH.indexOf(c);
  return i < 0 ? "_" : CODE[i];
}

function readJson(file) {
  try {
    return JSON.parse(fs.readFileSync(path.join(DIR, file), "utf8"));
  } catch (e) {
    return null;
  }
}

function shardFor(w) {
  if (!split) split = new Set(((readJson("index.json") || {}).split) || []);
  let k = code(w[0]) + (w.length > 1 ? code(w[1]) : "_");
  if (split.has(k)) k += w.length > 2 ? code(w[2]) : "_";
  return k;
}

function loadShard(k) {
  if (cache.has(k)) {
    const v = cache.get(k);
    cache.delete(k); cache.set(k, v);          // keep it recent
    return v;
  }
  const v = readJson(k + ".json") || {};
  cache.set(k, v);
  if (cache.size > 24) cache.delete(cache.keys().next().value);
  return v;
}

export function pymorphyLemmas(word) {
  const w = String(word || "").toLowerCase().replace(/́/g, "").trim();
  if (!w || !/^[а-яё-]+$/.test(w)) return null;
  const tryForm = function (f) {
    const raw = loadShard(shardFor(f))[f];
    if (!raw) return null;
    const known = raw[0] !== "?";
    const readings = raw.replace(/^\?/, "").split("|").map(function (r) {
      const i = r.lastIndexOf(":");
      return { lemma: i < 0 ? r : r.slice(0, i), pos: i < 0 ? "" : r.slice(i + 1) };
    }).filter(function (r) { return r.lemma; });
    return readings.length ? { known: known, readings: readings } : null;
  };
  // The table spells ё where the dictionary does; a book often prints е.
  return tryForm(w) || (w.indexOf("ё") >= 0 ? tryForm(w.replace(/ё/g, "е")) : null);
}
