// Curated slang glossary + dictionary miss log, both stored in R2.
//
// Why this exists: Yandex and English Wiktionary between them cover ordinary
// Russian and a fair slice of criminal slang, but блатной жаргон and modern
// сленг have a long tail neither reaches — малява, банковать, and most of what
// Круг sings about. That tail is finite (the library is bounded), so it is
// worth curating by hand rather than guessing at runtime.
//
// Two glossary objects, merged at read time:
//   dict/slang-seed.json   bulk, harvested by tools/fetch_zhargon.py and
//                          pushed with rclone — safe to overwrite wholesale
//   dict/slang.json        entries added by hand from the reader popup;
//                          wins over the seed on a key collision
// Plus:
//   dict/misses.json       every word all tiers failed, with a hit count, so
//                          the next words worth curating are always known
//
// Entry shape is the same object /api/define returns, so nothing downstream
// needs to know a definition came from here.

import { S3Client, GetObjectCommand, PutObjectCommand } from "@aws-sdk/client-s3";

const BUCKET = process.env.R2_BUCKET || "govorim-audio";
const SEED_KEY = "dict/slang-seed.json";
const HAND_KEY = "dict/slang.json";
const MISS_KEY = "dict/misses.json";

let s3 = null;
function getS3() {
  if (!s3) {
    s3 = new S3Client({
      region: "auto",
      endpoint: process.env.R2_ENDPOINT,
      credentials: {
        accessKeyId: process.env.R2_ACCESS_KEY_ID,
        secretAccessKey: process.env.R2_SECRET_ACCESS_KEY,
      },
    });
  }
  return s3;
}

function r2Configured() {
  return !!(process.env.R2_ENDPOINT && process.env.R2_ACCESS_KEY_ID && process.env.R2_SECRET_ACCESS_KEY);
}

async function r2GetJson(key) {
  try {
    const resp = await getS3().send(new GetObjectCommand({ Bucket: BUCKET, Key: key }));
    return JSON.parse(await resp.Body.transformToString());
  } catch (e) {
    if (e.name === "NoSuchKey" || (e.$metadata && e.$metadata.httpStatusCode === 404)) return null;
    throw e;
  }
}

async function r2PutJson(key, data) {
  await getS3().send(new PutObjectCommand({
    Bucket: BUCKET,
    Key: key,
    Body: JSON.stringify(data, null, 1),
    ContentType: "application/json",
  }));
}

// ---- key normalisation -----------------------------------------------------
// Jargon is not inflected predictably and Yandex's MORPHO flag never sees these
// words, so an entry may list extra surface forms of its own. Keys fold case
// and ё so «малЯва» and «Малява» land on the same entry.

export function dictKey(word) {
  return String(word || "").trim().toLowerCase().replace(/ё/g, "е");
}

// ---- glossary --------------------------------------------------------------
// Cached in module scope: a warm Vercel function then answers a glossary hit
// with no R2 round trip at all. Short TTL so an entry added from the popup
// shows up on the next lookup rather than the next cold start.

const GLOSSARY_TTL_MS = 60 * 1000;
let glossaryCache = null;
let glossaryAt = 0;

function indexEntries(map, into, origin) {
  // A bulk-harvested file repeats the same attribution on every entry, so the
  // harvester writes it once into _meta and each entry inherits it. Saved 452KB
  // on a 1886-word seed.
  const meta = (map && map._meta) || {};
  for (const rawKey of Object.keys(map || {})) {
    if (rawKey.startsWith("_")) continue;         // _meta and friends
    const entry = map[rawKey];
    if (!entry || typeof entry !== "object") continue;
    if (!entry.source && meta.source) entry.source = meta.source;
    if (!entry.sourceUrl && meta.sourceUrl) entry.sourceUrl = meta.sourceUrl;
    const keys = [rawKey].concat(Array.isArray(entry.forms) ? entry.forms : []);
    for (const k of keys) {
      const key = dictKey(k);
      if (key) into.set(key, { entry: entry, lemma: entry.lemma || rawKey, origin: origin });
    }
  }
}

export async function loadGlossary(force) {
  const now = Date.now();
  if (!force && glossaryCache && now - glossaryAt < GLOSSARY_TTL_MS) return glossaryCache;
  if (!r2Configured()) return new Map();

  const index = new Map();
  const [seed, hand] = await Promise.all([
    r2GetJson(SEED_KEY).catch(function () { return null; }),
    r2GetJson(HAND_KEY).catch(function () { return null; }),
  ]);
  // Seed first, hand-written second: a word curated from the popup overrides
  // whatever the bulk harvest said about it.
  indexEntries(seed, index, "seed");
  indexEntries(hand, index, "hand");

  glossaryCache = index;
  glossaryAt = now;
  return index;
}

// Map a stored entry onto the response shape the popup already consumes.
export function glossaryEntry(hit, clickedWord, matchedForm) {
  const e = hit.entry;
  const translation = String(e.translation || e.en || "").trim();
  if (!translation) return null;
  return {
    word: clickedWord,
    lemma: hit.lemma || matchedForm || clickedWord,
    matchedForm: matchedForm,
    partOfSpeech: String(e.partOfSpeech || "").toLowerCase(),
    aspect: e.aspect || "",
    aspectPair: e.aspectPair || "",
    translation: translation,
    definitionRu: e.definitionRu || e.ru || "",
    grammar: [e.register || "", e.grammar || ""].filter(Boolean).join(" · "),
    example: e.example || "",
    exampleTranslation: e.exampleTranslation || "",
    definitionSource: "glossary",
    sourceUrl: e.sourceUrl || "",
    sourceNote: e.source || "",
  };
}

// Add or replace one hand-curated entry. Read-merge-write on a single small
// object: there is exactly one admin writing it, so a lost update needs two
// browser tabs racing each other.
export async function putGlossaryEntry(word, entry) {
  if (!r2Configured()) throw new Error("R2 is not configured on this deployment");
  const key = dictKey(word);
  if (!key) throw new Error("Empty word");
  const hand = (await r2GetJson(HAND_KEY)) || {};
  hand[key] = entry;
  await r2PutJson(HAND_KEY, hand);
  glossaryCache = null;                    // next lookup re-reads
  return Object.keys(hand).filter(function (k) { return !k.startsWith("_"); }).length;
}

export async function removeMiss(word) {
  if (!r2Configured()) return;
  const key = dictKey(word);
  const misses = await r2GetJson(MISS_KEY);
  if (!misses || !misses[key]) return;
  delete misses[key];
  await r2PutJson(MISS_KEY, misses);
}

// ---- miss log --------------------------------------------------------------
// Every word no tier could answer, with a count. Misses are CDN-cached for a
// day, so a repeated word costs one write per day at most, and the counts
// still rank the tail by how often it actually interrupts reading.

export async function logMiss(word, context) {
  if (!r2Configured()) return;
  const key = dictKey(word);
  if (!key) return;
  const misses = (await r2GetJson(MISS_KEY)) || {};
  const now = new Date().toISOString().slice(0, 10);
  const rec = misses[key] || { count: 0, first: now };
  rec.count += 1;
  rec.last = now;
  if (context && !rec.context) rec.context = String(context).slice(0, 120);
  misses[key] = rec;
  await r2PutJson(MISS_KEY, misses);
}

export async function listMisses() {
  if (!r2Configured()) return [];
  const misses = (await r2GetJson(MISS_KEY)) || {};
  return Object.keys(misses)
    .map(function (w) { return Object.assign({ word: w }, misses[w]); })
    .sort(function (a, b) { return (b.count || 0) - (a.count || 0); });
}
