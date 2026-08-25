// Serverless function: word definitions from the Yandex Dictionary API,
// with English Wiktionary as a free, keyless second tier behind it.
//
// The old path sent every word tap through Gemini (/api/chat). This endpoint
// replaces that with a real dictionary: instant, deterministic, and free
// (10,000 lookups/day on the free key). Words Yandex has never heard of —
// archaic, dialect and literary forms, which is most of what a 19th-century
// novel throws at you — fall through to Wiktionary instead of to an AI.
//
// Required env var on Vercel:
//   YANDEX_DICT_KEY — free key from https://yandex.com/dev/dictionary/keys/get/
// Optional:
//   WIKTIONARY_FALLBACK — set to "0" to switch the second tier off.
//
// Notes:
// - MORPHO flag (0x0004) makes Yandex accept inflected forms: looking up
//   "столе" returns the entry for "стол", which is exactly what a reader
//   clicking mid-sentence needs. The entry's own text IS the lemma.
// - Yandex is picky about е/ё in some entries, so on a miss we retry the
//   lowercase form and up to three ё-variants server-side before giving up.
// - A second lookup in ru-ru supplies Russian synonyms for the popup's
//   "Russian definition" line. Its failure is never fatal.
// - Responses carry s-maxage so Vercel's CDN caches each word; repeat lookups
//   of "который" cost neither quota nor a function invocation.
// - Yandex's terms require the visible text "Powered by Yandex.Dictionary" —
//   the popup renders it whenever definitionSource === "yandex".

import { currentUser } from "../lib/auth.js";
import {
  loadGlossary, glossaryEntry, putGlossaryEntry, dictKey,
  logMiss, listMisses, removeMiss,
} from "../lib/dict.js";
import { ruWiktionaryLookup } from "../lib/ruwikt.js";

const YANDEX_URL = "https://dictionary.yandex.net/api/v1/dicservice.json/lookup";
const FLAG_MORPHO = 0x0004;

// ---- Per-IP rate limit (same shape as api/chat.js) -------------------------
// Generous compared to the AI path — a lookup costs nothing — but still a cap
// so one IP can't drain the shared 10k/day Yandex quota.
const rateLimitMap = new Map();
const RATE_WINDOW_MS = 60 * 1000;
const RATE_MAX_PER_WINDOW = 40;
const RATE_DAILY_PER_IP = 1200;
const RATE_MAX_PER_WINDOW_ANON = 20;
const RATE_DAILY_PER_IP_ANON = 400;

function getClientIp(req) {
  const fwd = req.headers["x-forwarded-for"];
  if (typeof fwd === "string" && fwd.length) return fwd.split(",")[0].trim();
  return req.headers["x-real-ip"] || "unknown";
}

function checkRateLimit(ip, signedIn) {
  const perWindow = signedIn ? RATE_MAX_PER_WINDOW : RATE_MAX_PER_WINDOW_ANON;
  const perDay = signedIn ? RATE_DAILY_PER_IP : RATE_DAILY_PER_IP_ANON;
  const now = Date.now();
  const day = Math.floor(now / (24 * 60 * 60 * 1000));
  const rec = rateLimitMap.get(ip) || { hits: [], dailyKey: day, dailyCount: 0 };
  if (rec.dailyKey !== day) { rec.dailyKey = day; rec.dailyCount = 0; }
  rec.hits = rec.hits.filter(function (t) { return now - t < RATE_WINDOW_MS; });
  if (rec.hits.length >= perWindow) return { ok: false, reason: "Too many lookups this minute. Wait a bit." };
  if (rec.dailyCount >= perDay) return { ok: false, reason: "Daily lookup limit reached for your IP. Try tomorrow." };
  rec.hits.push(now);
  rec.dailyCount += 1;
  rateLimitMap.set(ip, rec);
  return { ok: true };
}

// ---- Yandex plumbing -------------------------------------------------------

async function yandexLookup(text, lang, signal) {
  const url =
    YANDEX_URL +
    "?key=" + encodeURIComponent(process.env.YANDEX_DICT_KEY) +
    "&lang=" + lang +
    "&ui=en" +
    "&flags=" + FLAG_MORPHO +
    "&text=" + encodeURIComponent(text);
  const resp = await fetch(url, { signal });
  if (!resp.ok) {
    const err = new Error("Yandex returned HTTP " + resp.status);
    err.yandexStatus = resp.status;
    throw err;
  }
  const data = await resp.json();
  return Array.isArray(data && data.def) ? data.def : [];
}

function yoVariants(word) {
  const out = [];
  for (let i = 0; i < word.length; i++) {
    if (word[i] === "е") out.push(word.slice(0, i) + "ё" + word.slice(i + 1));
  }
  return out;
}

// Yandex grammatical tags arrive in whatever language `ui` selects, and have
// varied historically — normalize defensively.
function normalizeAspect(asp) {
  const a = (asp || "").toLowerCase();
  if (!a) return "";
  if (/несов|impf|imperf/.test(a)) return "imperfective";
  if (/сов|pf|perf/.test(a)) return "perfective";
  return "";
}

function genderWord(gen) {
  const g = (gen || "").toLowerCase();
  if (/^м|^m/.test(g) && !/ср|neut/.test(g)) return "masculine";
  if (/^ж|^f/.test(g)) return "feminine";
  if (/^с|^n/.test(g)) return "neuter";
  return "";
}

// One translation line, enriched with the Russian sense marker when Yandex
// supplies one — polysemy like лук → "onion (растение), bow (оружие)".
function translationLine(tr, isVerb) {
  let t = (tr.text || "").trim();
  if (!t) return "";
  if (isVerb && !/^to\s/i.test(t)) t = "to " + t;
  const mean = Array.isArray(tr.mean) && tr.mean.length ? tr.mean[0].text : "";
  return mean ? t + " (" + mean + ")" : t;
}

// Map Yandex's def[] onto the exact shape the popup and the vocab list
// already consume (same fields the old AI prompt produced).
function buildEntry(defs, clickedWord, matchedForm) {
  const primary = defs[0];
  const lemma = (primary.text || matchedForm || clickedWord).trim();
  const pos = (primary.pos || "").toLowerCase();
  const isVerb = pos.indexOf("verb") !== -1 || pos.indexOf("глагол") !== -1;

  const trs = Array.isArray(primary.tr) ? primary.tr : [];
  const translation = trs.slice(0, 4)
    .map(function (t) { return translationLine(t, isVerb); })
    .filter(Boolean)
    .join(", ");

  const aspect = normalizeAspect(primary.asp);
  const gender = genderWord(primary.gen);

  const grammarBits = [];
  if (gender) grammarBits.push(gender + " noun");
  else if (isVerb && aspect) grammarBits.push(aspect + " verb");
  if (primary.ts) grammarBits.push("[" + primary.ts + "]");
  // A word that is also a different part of speech (стекло: noun AND verb
  // form) gets a compact mention instead of being silently dropped.
  for (let i = 1; i < Math.min(defs.length, 3); i++) {
    const d = defs[i];
    const firstTr = d.tr && d.tr[0] ? d.tr[0].text : "";
    if (firstTr) grammarBits.push("also " + (d.pos || "?") + ": " + (d.text || lemma) + " — " + firstTr);
  }

  // First example that comes with its own translation.
  let example = "", exampleTranslation = "";
  for (const t of trs) {
    const exs = Array.isArray(t.ex) ? t.ex : [];
    for (const ex of exs) {
      if (ex.text && ex.tr && ex.tr[0] && ex.tr[0].text) {
        example = ex.text;
        exampleTranslation = ex.tr[0].text;
        break;
      }
    }
    if (example) break;
  }

  return {
    word: clickedWord,
    lemma: lemma,
    matchedForm: matchedForm,
    partOfSpeech: pos || "",
    aspect: aspect,
    aspectPair: "",           // Yandex doesn't state aspect partners reliably
    translation: translation,
    definitionRu: "",         // filled from the ru-ru lookup below when it works
    grammar: grammarBits.join(" · "),
    example: example,
    exampleTranslation: exampleTranslation,
    definitionSource: "yandex",
  };
}


// ---- Wiktionary fallback ---------------------------------------------------
// Yandex is a modern learner's dictionary: excellent on everyday vocabulary,
// silent on exactly the words the library is full of (davecha, treugolka,
// archaic participles, dialect spellings). English Wiktionary covers that long
// tail, so a Yandex miss falls through to it via freedictionaryapi.com — a
// free, keyless JSON view over the same Wiktionary data. Their cap is 1000
// requests/hour per IP; the CDN cache below keeps us nowhere near it.
//
// Wiktionary text is CC BY-SA 4.0, so these entries carry
// definitionSource === "wiktionary" plus a sourceUrl, and the popup renders
// the attribution line the licence requires.

const WIKT_URL = "https://freedictionaryapi.com/api/v1/entries/ru/";
const COMBINING = /[\u0300-\u036f]/g;   // stress marks live in the canonical form

function deaccent(s) { return (s || "").replace(COMBINING, "").trim(); }

function hasTag(tags, name) {
  return Array.isArray(tags) && tags.some(function (t) { return String(t).toLowerCase() === name; });
}

function isFormOf(sense) { return hasTag(sense && sense.tags, "form of"); }

async function wiktFetch(word, signal) {
  const resp = await fetch(WIKT_URL + encodeURIComponent(word), {
    signal,
    headers: { accept: "application/json", "user-agent": "govorim.dev dictionary lookup" },
  });
  if (resp.status === 404) return null;
  if (!resp.ok) {
    const err = new Error("Wiktionary returned HTTP " + resp.status);
    err.wiktStatus = resp.status;
    throw err;
  }
  const data = await resp.json();
  const all = Array.isArray(data && data.entries) ? data.entries : [];
  const ru = all.filter(function (e) { return e && e.language && e.language.code === "ru"; });
  if (!ru.length) return null;
  return { entries: ru, sourceUrl: (data.source && data.source.url) || "" };
}

// The canonical form carries the stress mark and the grammatical tags.
function canonicalForm(entry) {
  const forms = Array.isArray(entry.forms) ? entry.forms : [];
  for (const f of forms) if (hasTag(f.tags, "canonical")) return f;
  return null;
}

function definedSenses(entry) {
  const senses = Array.isArray(entry && entry.senses) ? entry.senses : [];
  return senses.filter(function (s) { return s && s.definition; });
}

function realSenses(entry) {
  const defined = definedSenses(entry);
  const real = defined.filter(function (s) { return !isFormOf(s); });
  return real.length ? real : defined;
}

// Prefer the entry that actually means something over one that only says
// "genitive plural of ..." — a word can be both (stekló: noun and verb form).
function pickEntry(entries) {
  let best = null, bestScore = -1;
  for (const e of entries) {
    const defined = definedSenses(e);
    const real = defined.filter(function (s) { return !isFormOf(s); });
    const score = real.length * 10 + defined.length;
    if (score > bestScore) { bestScore = score; best = e; }
  }
  return best;
}

// "prepositional singular of stol (stol)" -> the Cyrillic lemma.
function lemmaPointer(entry) {
  for (const s of definedSenses(entry)) {
    const m = /\bof\s+([\u0400-\u04ff\u0300-\u036f-]+)/.exec(s.definition);
    if (m) return deaccent(m[1]);
  }
  return "";
}

// An imperfective entry lists its perfective partner(s) as bare single-tag
// forms; everything else in forms[] is the conjugation table or template noise.
// Yandex never gave us this, so the Wiktionary tier actually fills aspectPair.
function aspectPartners(entry, aspect) {
  const want = aspect === "imperfective" ? "perfective" : aspect === "perfective" ? "imperfective" : "";
  if (!want) return [];
  const forms = Array.isArray(entry.forms) ? entry.forms : [];
  const out = [];
  for (const f of forms) {
    if (!f || !f.word || f.word === "-") continue;
    if (Array.isArray(f.tags) && f.tags.length === 1 && f.tags[0] === want) {
      const w = deaccent(f.word);
      if (w && out.indexOf(w) === -1) out.push(w);
    }
  }
  return out.slice(0, 3);
}

// Map a Wiktionary pack onto the same entry shape the popup and the vocab
// list already consume, so nothing downstream needs to know where it came from.
function buildWiktEntry(pack, clickedWord, matchedForm, formNote) {
  const entry = pickEntry(pack.entries);
  if (!entry) return null;

  const canon = canonicalForm(entry);
  const accented = canon ? canon.word : "";
  const canonTags = (canon && canon.tags) || [];
  const lemma = deaccent(accented) || deaccent(entry.word) || matchedForm || clickedWord;

  const senses = realSenses(entry);
  const translation = senses.slice(0, 4)
    .map(function (s) { return String(s.definition).trim(); })
    .filter(Boolean)
    .join("; ");
  if (!translation) return null;

  let aspect = "";
  if (hasTag(canonTags, "imperfective")) aspect = "imperfective";
  else if (hasTag(canonTags, "perfective")) aspect = "perfective";

  let gender = "";
  if (hasTag(canonTags, "masculine")) gender = "masculine";
  else if (hasTag(canonTags, "feminine")) gender = "feminine";
  else if (hasTag(canonTags, "neuter")) gender = "neuter";

  const pair = aspectPartners(entry, aspect);

  const bits = [];
  if (accented && accented !== lemma) bits.push(accented);
  if (gender) bits.push(gender + " noun");
  else if (aspect) bits.push(aspect + " verb");
  if (pair.length) bits.push((aspect === "imperfective" ? "pf. " : "impf. ") + pair.join(", "));
  const ipa = (Array.isArray(entry.pronunciations) ? entry.pronunciations : [])
    .filter(function (p) { return p && p.type === "ipa" && p.text && (!p.tags || !p.tags.length); })[0];
  if (ipa) bits.push(ipa.text);
  if (formNote) bits.push(formNote);
  for (const other of pack.entries) {
    if (other === entry || bits.length > 6) continue;
    const os = realSenses(other)[0];
    if (os) bits.push("also " + (other.partOfSpeech || "?") + ": " + String(os.definition).slice(0, 60));
  }

  const syns = [];
  const addSyns = function (list) {
    (Array.isArray(list) ? list : []).forEach(function (x) {
      const w = deaccent(typeof x === "string" ? x : (x && x.word) || "");
      if (w && w.toLowerCase() !== lemma.toLowerCase() && syns.indexOf(w) === -1) syns.push(w);
    });
  };
  addSyns(entry.synonyms);
  senses.forEach(function (s) { addSyns(s.synonyms); });

  // Wiktionary examples are Russian-only (no gloss), and quotes can be a whole
  // Bible verse — take the shortest useful thing and cap it.
  let example = "";
  for (const s of senses) {
    const exs = Array.isArray(s.examples) ? s.examples : [];
    for (const ex of exs) {
      const t = (typeof ex === "string" ? ex : (ex && ex.text) || "").trim();
      if (t) { example = t; break; }
    }
    if (example) break;
    const qs = Array.isArray(s.quotes) ? s.quotes : [];
    if (qs.length && qs[0] && qs[0].text) { example = String(qs[0].text).trim(); break; }
  }
  if (example.length > 180) example = example.slice(0, 177) + "…";

  return {
    word: clickedWord,
    lemma: lemma,
    matchedForm: matchedForm,
    partOfSpeech: (entry.partOfSpeech || "").toLowerCase(),
    aspect: aspect,
    aspectPair: pair.join(", "),
    translation: translation,
    definitionRu: syns.length ? "≈ " + syns.slice(0, 5).join(", ") : "",
    grammar: bits.join(" · "),
    example: example,
    exampleTranslation: "",
    definitionSource: "wiktionary",
    sourceUrl: pack.sourceUrl || "",
  };
}

// Two candidates only (as clicked, and the yo-folded spelling): Wiktionary
// indexes yo properly, so the variant spray Yandex needs would just burn time
// against this request's shared 10s budget.
async function wiktionaryLookup(candidates, clickedWord, signal) {
  for (const cand of candidates) {
    const pack = await wiktFetch(cand, signal);
    if (!pack) continue;

    const direct = pickEntry(pack.entries);
    const hasReal = definedSenses(direct).some(function (s) { return !isFormOf(s); });
    if (hasReal) {
      const built = buildWiktEntry(pack, clickedWord, cand, "");
      if (built) return built;
      continue;
    }

    // An inflected form: "stole" only says "prepositional singular of stol".
    // Follow that one hop for the actual meaning, keeping the grammatical note
    // so the reader still sees which case they clicked.
    const note = String((realSenses(direct)[0] || {}).definition || "").slice(0, 80);
    const ptr = lemmaPointer(direct || {});
    if (ptr && ptr !== cand) {
      const lemPack = await wiktFetch(ptr, signal);
      if (lemPack) {
        const built = buildWiktEntry(lemPack, clickedWord, cand, note);
        if (built) return built;
      }
    }
    const asIs = buildWiktEntry(pack, clickedWord, cand, "");
    if (asIs) return asIs;
  }
  return null;
}

// ---- Handler ---------------------------------------------------------------

export default async function handler(req, res) {
  // POST is the curator's door: the reader popup, for the admin account only,
  // writes a hand-authored entry for a word every tier missed. Folded into this
  // function rather than a new one — the Vercel free plan counts functions.
  if (req.method === "POST") return handleCurate(req, res);
  if (req.method !== "GET") return res.status(405).json({ error: "Method not allowed" });

  // ?misses=1 — the curation worklist, ranked by how often each word actually
  // interrupted reading. Admin only; never cached.
  if (req.query && req.query.misses) {
    const admin = currentUser(req);
    if (!admin || !admin.isAdmin) return res.status(403).json({ error: "Admin access required" });
    try {
      res.setHeader("Cache-Control", "no-store");
      return res.status(200).json({ misses: await listMisses() });
    } catch (e) {
      return res.status(502).json({ error: "Could not read the miss log: " + ((e && e.message) || "unknown") });
    }
  }

  const wiktEnabled = process.env.WIKTIONARY_FALLBACK !== "0";
  if (!process.env.YANDEX_DICT_KEY && !wiktEnabled) {
    return res.status(500).json({ error: "YANDEX_DICT_KEY not configured on the server" });
  }

  const raw = (req.query && req.query.word ? String(req.query.word) : "").trim();
  const word = raw.replace(/[^а-яёА-ЯЁ-]/g, "");
  if (!word || word.length < 2 || word.length > 50) {
    return res.status(400).json({ error: "Missing or invalid ?word=" });
  }

  const ip = getClientIp(req);
  const user = currentUser(req);
  // The offline desktop/Android build has no browser session — it serves the
  // app from localhost, so there is no cookie to send. It authenticates with a
  // shared secret instead (DESKTOP_KEY), which only sits in settings.json on
  // machines you control. Browsers still use the normal session path.
  const desktopKey = process.env.DESKTOP_KEY;
  const presented = req.headers["x-govorim-key"];
  const isDesktop = !!desktopKey && presented === desktopKey;
  // Site is account-gated; the anonymous tier below is retained only so the
  // limiter's shape matches api/chat.js.
  if (!user && !isDesktop) {
    return res.status(401).json({ error: "An account is required. Create one — it is instant and free." });
  }
  const rl = checkRateLimit(ip, !!user || isDesktop);
  if (!rl.ok) return res.status(429).json({ error: rl.reason });

  // The whole request — every variant plus the ru-ru pass — shares one budget.
  const ctrl = new AbortController();
  const timer = setTimeout(function () { ctrl.abort(); }, 10000);

  try {
    // Try the word as clicked, then lowercase, then BOTH directions of the
    // е/ё mess. MORPHO handles inflection; this loop only handles casing and
    // spelling. The ё→е direction matters most: Russian dictionaries index
    // the е-form of most words, so a text that prints "её", "всё" or "живёт"
    // misses on the literal spelling and only resolves once ё is folded away.
    // Missing that direction sent every ё-carrying word to the AI fallback,
    // which is why some books burned the quota and others did not.
    const lower = word.toLowerCase();
    const deyo = lower.replace(/ё/g, "е");
    const candidates = [word, lower, deyo]
      .concat(yoVariants(deyo).slice(0, 3))
      .filter(function (w, i, arr) { return arr.indexOf(w) === i; });

    // -- 0. Curated glossary ------------------------------------------------
    // Checked first, not last: an entry here was written by hand on purpose, so
    // it should win even where Yandex has some blander sense of the word. This
    // is also the only tier that knows блатной жаргон reliably.
    try {
      const glossary = await loadGlossary(false);
      for (const cand of [lower, deyo]) {
        const hit = glossary.get(dictKey(cand));
        if (hit) {
          const built = glossaryEntry(hit, word, cand);
          if (built) {
            // Short cache: a word curated from the popup should show its new
            // definition on the next tap, not in a week.
            res.setHeader("Cache-Control", "public, s-maxage=60");
            return res.status(200).json(built);
          }
        }
      }
    } catch (e) {
      console.warn("[define] glossary unavailable:", (e && e.message) || e);
    }

    let defs = [], matchedForm = "", yandexErr = null;
    if (process.env.YANDEX_DICT_KEY) {
      try {
        for (const cand of candidates) {
          defs = await yandexLookup(cand, "ru-en", ctrl.signal);
          if (defs.length) { matchedForm = cand; break; }
        }
      } catch (e) {
        // A Yandex outage or an exhausted daily quota must not take the whole
        // lookup down — Wiktionary can still answer. Keep the error and
        // rethrow it only if that tier comes up empty as well.
        if (e && e.name === "AbortError") throw e;
        yandexErr = e;
        defs = [];
      }
    }

    if (!defs.length) {
      if (wiktEnabled) {
        const wiktCands = [lower, deyo].filter(function (w, i, arr) { return w && arr.indexOf(w) === i; });
        let wikt = null;
        try {
          wikt = await wiktionaryLookup(wiktCands, word, ctrl.signal);
        } catch (e) {
          if (e && e.name === "AbortError") throw e;
          console.warn("[define] Wiktionary tier failed:", (e && e.message) || e);
        }
        if (wikt) {
          res.setHeader("Cache-Control", "public, s-maxage=604800, stale-while-revalidate=86400");
          return res.status(200).json(wikt);
        }
      }

      // -- 3. ru.wiktionary ---------------------------------------------------
      // Last automatic tier, and the one that actually knows жаргон. Its
      // definitions are Russian unless the entry carries a Перевод block.
      if (process.env.RUWIKT_FALLBACK !== "0") {
        const ruCands = [lower, deyo].filter(function (w, i, arr) { return w && arr.indexOf(w) === i; });
        let ruWikt = null;
        try {
          ruWikt = await ruWiktionaryLookup(ruCands, word, ctrl.signal);
        } catch (e) {
          if (e && e.name === "AbortError") throw e;
          console.warn("[define] ru.wiktionary tier failed:", (e && e.message) || e);
        }
        if (ruWikt) {
          res.setHeader("Cache-Control", "public, s-maxage=604800, stale-while-revalidate=86400");
          return res.status(200).json(ruWikt);
        }
      }

      if (yandexErr) throw yandexErr;

      // Nothing anywhere. Record it so the curation worklist grows itself:
      // this is exactly the tail worth adding to the glossary by hand.
      try { await logMiss(word, req.query && req.query.ctx); }
      catch (e) { console.warn("[define] could not log miss:", (e && e.message) || e); }

      // Cache misses too — no tier's coverage changes hour to hour, and repeat
      // misses on the same rare word shouldn't spend quota or R2 writes.
      res.setHeader("Cache-Control", "public, s-maxage=86400");
      return res.status(404).json({ error: 'No dictionary entry found for "' + word + '"', noEntry: true });
    }

    const entry = buildEntry(defs, word, matchedForm);

    // Russian synonyms for the monolingual line. Strictly best-effort.
    try {
      const ruDefs = await yandexLookup(entry.lemma, "ru-ru", ctrl.signal);
      if (ruDefs.length && Array.isArray(ruDefs[0].tr)) {
        const syns = ruDefs[0].tr.map(function (t) { return t.text; })
          .filter(function (t) { return t && t.toLowerCase() !== entry.lemma.toLowerCase(); })
          .slice(0, 5);
        if (syns.length) entry.definitionRu = "≈ " + syns.join(", ");
      }
    } catch (_) { /* synonyms are a garnish */ }

    // A week at the CDN: dictionary entries do not change. The browser also
    // caches in localStorage, so this mostly serves other users of the word.
    res.setHeader("Cache-Control", "public, s-maxage=604800, stale-while-revalidate=86400");
    return res.status(200).json(entry);
  } catch (err) {
    const ys = err && err.yandexStatus;
    if (ys === 401 || ys === 402) {
      return res.status(500).json({ error: "Yandex API key invalid or blocked — check YANDEX_DICT_KEY" });
    }
    if (ys === 403) {
      // Yandex's daily quota, not ours. Client falls back to the AI define.
      return res.status(429).json({ error: "Yandex daily lookup quota exhausted — resets at midnight UTC" });
    }
    if (err && err.name === "AbortError") {
      return res.status(504).json({ error: "Dictionary service timed out" });
    }
    return res.status(502).json({ error: "Dictionary lookup failed: " + ((err && err.message) || "unknown error") });
  } finally {
    clearTimeout(timer);
  }
}

// ---- Curation (admin POST) -------------------------------------------------
// One hand-authored glossary entry, written straight from the reader popup.
// Keeps блатной жаргон curation where it actually happens — mid-page, at the
// moment the word stops you — instead of in a repo round trip.

async function handleCurate(req, res) {
  const user = currentUser(req);
  if (!user) return res.status(401).json({ error: "Not signed in" });
  if (!user.isAdmin) return res.status(403).json({ error: "Admin access required" });

  const body = (req.body && typeof req.body === "object") ? req.body : {};
  const word = String(body.word || "").trim().replace(/[^а-яёА-ЯЁ-]/g, "");
  const translation = String(body.translation || "").trim();
  if (!word) return res.status(400).json({ error: "Missing word" });
  if (!translation) return res.status(400).json({ error: "A definition is required" });

  const clip = function (v, n) { return String(v || "").trim().slice(0, n); };
  const entry = {
    lemma: clip(body.lemma, 60) || word,
    partOfSpeech: clip(body.partOfSpeech, 30),
    register: clip(body.register, 60),
    translation: clip(translation, 400),
    definitionRu: clip(body.definitionRu, 400),
    example: clip(body.example, 300),
    exampleTranslation: clip(body.exampleTranslation, 300),
    source: clip(body.source, 120),
    // Jargon inflects unpredictably and no morphology tier ever sees these
    // words, so the curator can name extra surface forms that map here.
    forms: (Array.isArray(body.forms) ? body.forms : String(body.forms || "").split(/[,\s]+/))
      .map(function (f) { return String(f).trim().replace(/[^а-яёА-ЯЁ-]/g, ""); })
      .filter(Boolean).slice(0, 12),
    addedBy: user.email,
    addedAt: new Date().toISOString().slice(0, 10),
  };

  try {
    const total = await putGlossaryEntry(word, entry);
    try { await removeMiss(word); } catch (_) { /* the log is a convenience */ }
    const hit = { entry: entry, lemma: entry.lemma, origin: "hand" };
    return res.status(200).json({ ok: true, total: total, entry: glossaryEntry(hit, word, word) });
  } catch (e) {
    return res.status(502).json({ error: "Could not save the entry: " + ((e && e.message) || "unknown") });
  }
}
