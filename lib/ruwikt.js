// ---- ru.wiktionary fallback ------------------------------------------------
// Русский Викисловарь is where блатной жаргон actually lives: малява, банковать
// and most of what Круг sings about have entries there and nowhere else that is
// both free and licensed. Definitions come back in Russian; the Перевод block
// often carries an English column, so we use that as the headline when it
// exists and fall back to the Russian gloss when it doesn't.
//
// Parsed from raw wikitext via the MediaWiki API — there is no structured
// endpoint for ru.wiktionary the way freedictionaryapi.com serves the English
// one. The parse is deliberately forgiving: anything it can't recognise is
// dropped rather than guessed at.

const RUWIKT_API = "https://ru.wiktionary.org/w/api.php";

// Register templates worth surfacing, rendered in English so the popup reads
// consistently. Anything not listed here is dropped rather than shown raw.
const RU_LABELS = {
  "жарг": "jargon",
  "крим": "criminal slang",
  "угол": "criminal slang",
  "блат": "thieves' cant",
  "сленг": "slang",
  "мол": "youth slang",
  "прост": "low colloquial",
  "разг": "colloquial",
  "устар": "archaic",
  "истор": "historical",
  "рег": "regional",
  "обл": "dialectal",
  "бран": "abusive",
  "груб": "coarse",
  "неодобр": "derogatory",
  "пренебр": "disparaging",
  "ирон": "ironic",
  "шутл": "jocular",
  "перен": "figurative",
  "эвф": "euphemism",
  "поэт": "poetic",
  "воен": "military",
  "морск": "nautical",
  "карт": "card games",
};

async function ruWiktText(word, signal) {
  const url = RUWIKT_API +
    "?action=query&prop=revisions&rvprop=content&rvslots=main" +
    "&format=json&formatversion=2&redirects=1&origin=*" +
    "&titles=" + encodeURIComponent(word);
  const resp = await fetch(url, {
    signal,
    headers: { accept: "application/json", "user-agent": "govorim.dev dictionary lookup" },
  });
  if (!resp.ok) {
    const err = new Error("ru.wiktionary returned HTTP " + resp.status);
    err.ruWiktStatus = resp.status;
    throw err;
  }
  const data = await resp.json();
  const pages = (data && data.query && data.query.pages) || [];
  const page = pages[0];
  if (!page || page.missing) return null;
  const rev = page.revisions && page.revisions[0];
  const content = rev && rev.slots && rev.slots.main && rev.slots.main.content;
  return content || null;
}

// The Russian part of a page that may also describe Ukrainian, Bulgarian, etc.
// Headers are written several ways across the wiki's history, so match loosely
// and fall back to the whole page rather than returning nothing.
function russianSection(text) {
  const marker = /(^|\n)=\s*\{\{\s*(?:-ru-|язык\|ru|заголовок\|ru)[^}]*\}\}\s*=/i.exec(text);
  if (!marker) return text;
  const start = marker.index + marker[0].length;
  const rest = text.slice(start);
  const next = /\n=\s*\{\{\s*(?:-[a-z]{2,3}-|язык\|(?!ru\b))/i.exec(rest);
  return next ? rest.slice(0, next.index) : rest;
}

function sectionBody(text, name) {
  const re = new RegExp("\\n={2,5}\\s*" + name + "\\s*={2,5}\\s*\\n");
  const m = re.exec(text);
  if (!m) return "";
  const rest = text.slice(m.index + m[0].length);
  const next = /\n={2,5}[^=\n]/.exec(rest);
  return next ? rest.slice(0, next.index) : rest;
}

// Turn one wikitext definition line into plain text. Register templates become
// a bracketed English label; everything else templated is dropped.
function cleanWiki(line) {
  let labels = [];
  let s = line;

  s = s.replace(/<!--[\s\S]*?-->/g, "");
  s = s.replace(/<ref[^>]*>[\s\S]*?<\/ref>/gi, "").replace(/<ref[^>]*\/>/gi, "");
  s = s.replace(/\{\{\s*пример[\s\S]*?\}\}/gi, "");

  // Register/domain templates: {{жарг.|ru}}, {{крим.|ru|уточн.}}, {{разг.}}
  s = s.replace(/\{\{\s*([^|{}]+?)\.?\s*(\|[^{}]*)?\}\}/g, function (whole, name) {
    const key = String(name).trim().toLowerCase().replace(/\.$/, "");
    if (Object.prototype.hasOwnProperty.call(RU_LABELS, key)) {
      const label = RU_LABELS[key];
      if (labels.indexOf(label) === -1) labels.push(label);
      return "";
    }
    return "";
  });
  s = s.replace(/\{\{[\s\S]*?\}\}/g, "");          // any template that survived

  s = s.replace(/\[\[([^\]|]*)\|([^\]]*)\]\]/g, "$2");
  s = s.replace(/\[\[([^\]]*)\]\]/g, "$1");
  s = s.replace(/'''([^']*)'''/g, "$1").replace(/''([^']*)''/g, "$1");
  s = s.replace(/<[^>]+>/g, "");
  s = s.replace(/\s*[;,]\s*$/, "").replace(/\s{2,}/g, " ").trim();
  s = s.replace(/^[\s,;:.·◆•\-–—]+/, "").trim();   // templates leave orphan punctuation

  if (!s) return "";
  return labels.length ? "(" + labels.join(", ") + ") " + s : s;
}

function senseLines(body) {
  const out = [];
  for (const raw of body.split("\n")) {
    const line = raw.trim();
    if (!/^#[^:*]/.test(line) && line !== "#") continue;   // skip #: examples
    const cleaned = cleanWiki(line.replace(/^#+\s*/, ""));
    if (cleaned && out.indexOf(cleaned) === -1) out.push(cleaned);
  }
  return out;
}

// The Перевод block stores languages as |en=[[foo]], [[bar]] lines.
function englishFromTranslations(section) {
  const out = [];
  const re = /\|\s*en\s*=\s*([^\n|}]+)/g;
  let m;
  while ((m = re.exec(section))) {
    const cleaned = cleanWiki(m[1]);
    if (cleaned && out.indexOf(cleaned) === -1) out.push(cleaned);
  }
  return out;
}

function firstExample(body) {
  for (const raw of body.split("\n")) {
    const line = raw.trim();
    const m = /\{\{\s*пример\s*\|([^|}]*)/i.exec(line);
    if (m) {
      const ex = cleanWiki(m[1]);
      if (ex && ex.length > 4) return ex.length > 180 ? ex.slice(0, 177) + "…" : ex;
    }
  }
  return "";
}

function buildRuWiktEntry(text, clickedWord, matchedForm) {
  const ru = russianSection(text);
  const meaning = sectionBody(ru, "Значение");
  if (!meaning) return null;

  const senses = senseLines(meaning);
  if (!senses.length) return null;

  const english = englishFromTranslations(sectionBody(ru, "Перевод"));
  const syns = senseLines(sectionBody(ru, "Синонимы"))
    .join(", ").split(/,\s*/)
    .map(function (w) { return w.trim(); })
    .filter(function (w) { return w && w !== "-" && w.toLowerCase() !== matchedForm.toLowerCase(); })
    .slice(0, 5);

  // English headline when the Перевод block has one; otherwise the Russian
  // gloss carries the popup, and definitionRu is left empty so it isn't shown
  // twice.
  const hasEn = english.length > 0;
  const translation = hasEn ? english.slice(0, 4).join("; ") : senses.slice(0, 3).join("; ");
  if (!translation) return null;

  const bits = [];
  if (!hasEn) bits.push("Russian definition — no English in Викисловарь");
  if (syns.length) bits.push("≈ " + syns.join(", "));

  return {
    word: clickedWord,
    lemma: matchedForm,
    matchedForm: matchedForm,
    partOfSpeech: "",
    aspect: "",
    aspectPair: "",
    translation: translation,
    definitionRu: hasEn ? senses.slice(0, 3).join("; ") : "",
    grammar: bits.join(" · "),
    example: firstExample(meaning),
    exampleTranslation: "",
    definitionSource: "ruwiktionary",
    sourceUrl: "https://ru.wiktionary.org/wiki/" + encodeURIComponent(matchedForm),
  };
}

async function ruWiktionaryLookup(candidates, clickedWord, signal) {
  for (const cand of candidates) {
    const text = await ruWiktText(cand, signal);
    if (!text) continue;
    const built = buildRuWiktEntry(text, clickedWord, cand);
    if (built) return built;
  }
  return null;
}

// ---- Lemma resolution ------------------------------------------------------
// Yandex's MORPHO flag resolves inflected forms server-side, so a reader can
// tap any word in a sentence and get the dictionary entry. The Wiktionary tiers
// have no such thing: they are keyed by page title, and English Wiktionary
// carries form-of pages for only some Russian inflections. Tapping «банковал»
// or «фраера» therefore fell straight through to a 404 even though both lemmas
// are documented.
//
// MediaWiki's Russian search index IS stemmed, so one search request maps a
// surface form onto the page that exists. It is a search engine though, not a
// lemmatiser, so the result is only accepted when it looks like the same word:
// «фраера» → «фраер» passes, «давеча» → «недавно» does not.

function foldRu(s) {
  return String(s || "").trim().toLowerCase().replace(/ё/g, "е");
}

export function plausibleLemma(surface, title) {
  const a = foldRu(surface), b = foldRu(title);
  if (!a || !b || b === a) return false;
  if (/[\s(),.:]/.test(b)) return false;           // multi-word or disambiguated
  if (b.length > a.length + 3) return false;       // a lemma is rarely much longer
  let common = 0;
  while (common < a.length && common < b.length && a[common] === b[common]) common++;
  const need = Math.max(3, Math.ceil(0.6 * Math.min(a.length, b.length)));
  return common >= need;
}

export async function resolveLemma(word, signal) {
  const url = RUWIKT_API +
    "?action=query&list=search&srnamespace=0&srlimit=5" +
    "&format=json&formatversion=2&origin=*" +
    "&srsearch=" + encodeURIComponent(word);
  const resp = await fetch(url, {
    signal,
    headers: { accept: "application/json", "user-agent": "govorim.dev dictionary lookup" },
  });
  if (!resp.ok) return "";
  const data = await resp.json();
  const hits = (data && data.query && data.query.search) || [];
  for (const h of hits) {
    if (h && h.title && plausibleLemma(word, h.title)) return h.title;
  }
  return "";
}

export {
  ruWiktText, russianSection, sectionBody, cleanWiki, senseLines,
  englishFromTranslations, firstExample, buildRuWiktEntry, ruWiktionaryLookup,
  RU_LABELS,
};
