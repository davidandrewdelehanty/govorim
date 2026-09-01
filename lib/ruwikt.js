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

// Wikitext templates nest — {{пример|... {{выдел|малявой}} ...|автор|1977}} — so a
// non-greedy /\{\{.*?\}\}/ stops at the INNER close and spills the citation tail
// into the definition. Everything here scans braces properly instead.
function scanTemplates(s, onTemplate) {
  let out = "", i = 0;
  while (i < s.length) {
    const open = s.indexOf("{{", i);
    if (open === -1) { out += s.slice(i); break; }
    out += s.slice(i, open);
    let depth = 0, j = open;
    while (j < s.length) {
      if (s.startsWith("{{", j)) { depth++; j += 2; }
      else if (s.startsWith("}}", j)) { depth--; j += 2; if (depth === 0) break; }
      else j++;
    }
    if (depth !== 0) { out += s.slice(open); break; }     // unbalanced — leave as is
    out += onTemplate(s.slice(open + 2, j - 2));
    i = j;
  }
  return out;
}

// Split a template body on its top-level pipes only.
function templateArgs(inner) {
  const args = [];
  let depth = 0, cur = "";
  for (let i = 0; i < inner.length; i++) {
    if (inner.startsWith("{{", i) || inner.startsWith("[[", i)) { depth++; cur += inner.slice(i, i + 2); i++; continue; }
    if (inner.startsWith("}}", i) || inner.startsWith("]]", i)) { depth--; cur += inner.slice(i, i + 2); i++; continue; }
    if (inner[i] === "|" && depth === 0) { args.push(cur); cur = ""; continue; }
    cur += inner[i];
  }
  args.push(cur);
  return args;
}

function templateName(inner) {
  return templateArgs(inner)[0].trim().toLowerCase().replace(/\.$/, "");
}

// Templates that carry text we want to keep, unwrapped to their content.
const KEEP_INNER = new Set(["выдел", "-", "宽", "нп", "italic", "курсив"]);

function stripMarkup(s) {
  s = s.replace(/\[\[([^\]|]*)\|([^\]]*)\]\]/g, "$2");
  s = s.replace(/\[\[([^\]]*)\]\]/g, "$1");
  s = s.replace(/'''([^']*)'''/g, "$1").replace(/''([^']*)''/g, "$1");
  s = s.replace(/<[^>]+>/g, "");
  s = s.replace(/&nbsp;?/g, " ").replace(/&[a-z]+;/g, " ");
  s = s.replace(/[¶]/g, " ");
  return s;
}

function tidy(s) {
  s = s.replace(/\s{2,}/g, " ");
  s = s.replace(/\s+([,.;:!?])/g, "$1");
  s = s.replace(/^[\s,;:.·◆•\-–—]+/, "");
  s = s.replace(/[\s,;:·\-–—]+$/, "");
  return s.trim();
}

// Turn one wikitext definition line into plain text. Register templates become a
// bracketed English label; citation templates are dropped whole.
function cleanWiki(line) {
  const labels = [];
  let s = line;

  s = s.replace(/<!--[\s\S]*?-->/g, "");
  s = s.replace(/<ref[^>]*>[\s\S]*?<\/ref>/gi, "").replace(/<ref[^>]*\/>/gi, "");

  s = scanTemplates(s, function (inner) {
    const name = templateName(inner);
    if (Object.prototype.hasOwnProperty.call(RU_LABELS, name)) {
      const label = RU_LABELS[name];
      if (labels.indexOf(label) === -1) labels.push(label);
      return "";
    }
    if (KEEP_INNER.has(name)) {
      const args = templateArgs(inner);
      return cleanWiki(args.length > 1 ? args[1] : args[0]);
    }
    return "";                     // пример, источник, unknown — all dropped
  });

  s = tidy(stripMarkup(s));
  if (!s) return "";
  if (s.length > 200) s = s.slice(0, 197).replace(/\s+\S*$/, "") + "…";
  return labels.length ? "(" + labels.join(", ") + ") " + s : s;
}

function senseLines(body) {
  const out = [];
  for (const raw of body.split("\n")) {
    const line = raw.trim();
    if (!/^#[^:*]/.test(line)) continue;              // #: and #* are citations
    const cleaned = cleanWiki(line.replace(/^#+\s*/, ""));
    if (cleaned && cleaned.length > 1 && out.indexOf(cleaned) === -1) out.push(cleaned);
  }
  return out;
}

// The Перевод block stores languages as |en=[[foo]], [[bar]] lines.
function englishFromTranslations(section) {
  const out = [];
  const re = /\|\s*en\s*=\s*([^\n|}]+)/g;
  let m;
  while ((m = re.exec(section))) {
    let cleaned = cleanWiki(m[1]);
    // Translators' notes in the Russian original ("(неполное соответствие)")
    // are about the gloss, not part of it.
    cleaned = tidy(cleaned.replace(/\([^)]*[а-яё][^)]*\)/gi, ""));
    if (cleaned && out.indexOf(cleaned) === -1) out.push(cleaned);
  }
  return out;
}

// ru.wiktionary entries often carry {{audio|Ru-слово.ogg}} — a recording made
// by a native speaker and hosted on Wikimedia Commons. Special:FilePath resolves
// a bare filename to the file with no API call, so knowing the name is enough.
function audioFile(text) {
  let found = "";
  scanTemplates(text, function (inner) {
    if (found) return "";
    const args = templateArgs(inner);
    const name = String(args[0] || "").trim().toLowerCase().replace(/\.$/, "");
    if (name !== "audio") return "";
    for (const a of args.slice(1)) {
      const v = String(a).trim();
      if (/\.(ogg|oga|mp3|wav|flac)$/i.test(v)) { found = v; break; }
    }
    return "";
  });
  return found;
}

function commonsAudioUrl(filename) {
  if (!filename) return "";
  return "https://commons.wikimedia.org/wiki/Special:FilePath/" +
    encodeURIComponent(filename.replace(/ /g, "_"));
}

// The first usage example, unwrapped from its citation template.
function firstExample(body) {
  let found = "";
  for (const raw of body.split("\n")) {
    if (found) break;
    scanTemplates(raw, function (inner) {
      if (found) return "";
      if (templateName(inner) !== "пример") return "";
      const args = templateArgs(inner);
      const ex = tidy(stripMarkup(cleanWiki(args[1] || "")));
      if (ex && ex.length > 4) found = ex.length > 180 ? ex.slice(0, 177).replace(/\s+\S*$/, "") + "…" : ex;
      return "";
    });
  }
  return found;
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
    // A register label belongs to the sense, not to each synonym listed under it.
    .map(function (w) { return w.replace(/^\([^)]*\)\s*/, "").trim(); })
    .filter(function (w) { return w && w !== "-" && w !== "?" && w.length > 1 && w.toLowerCase() !== matchedForm.toLowerCase(); })
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
    // The entry had no Перевод block, so `translation` above is Russian. The
    // handler uses this to fetch an English hint before answering.
    noEnglish: !hasEn,
    definitionSource: "ruwiktionary",
    sourceUrl: "https://ru.wiktionary.org/wiki/" + encodeURIComponent(matchedForm),
    audioUrl: commonsAudioUrl(audioFile(ru)),
  };
}

async function ruWiktionaryLookup(candidates, clickedWord, signal, timeLeft) {
  for (const cand of candidates) {
    // The lemma guesser can hand several confirmed candidates down; Vercel
    // kills the function at ten seconds, so stop trying rather than be killed.
    if (timeLeft && timeLeft() < 1200) break;
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
  if (common < need) return false;
  // A shared prefix alone is not enough: «кент» and «кентавр» share four
  // letters and are unrelated. What separates an inflection from a different
  // word is that only the ENDINGS differ, and endings are short.
  if (b.length - common > 2) return false;   // candidate adds a whole new tail
  if (a.length - common > 4) return false;   // surface form is not just inflected
  return true;
}

// Which of these titles are real Викисловарь pages, in the order given.
//
// One request settles a whole list — MediaWiki takes up to 50 titles at a time
// — which is what makes guessing at the lemma affordable: a dozen rewrites of
// an ending cost exactly one round trip to find out which of them is a word.
export async function existingTitles(titles, signal) {
  const list = (titles || []).filter(Boolean).slice(0, 40);
  if (!list.length) return [];
  const url = RUWIKT_API +
    "?action=query&format=json&formatversion=2&origin=*" +
    "&titles=" + encodeURIComponent(list.join("|"));
  const resp = await fetch(url, {
    signal,
    headers: { accept: "application/json", "user-agent": "govorim.dev dictionary lookup" },
  });
  if (!resp.ok) return [];
  const data = await resp.json();
  const pages = (data && data.query && data.query.pages) || [];
  const live = Object.create(null);
  for (const pg of pages) {
    if (pg && !pg.missing && !pg.invalid && pg.title) live[String(pg.title).toLowerCase()] = true;
  }
  return list.filter(function (t) { return live[String(t).toLowerCase()]; });
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
  scanTemplates, templateArgs, audioFile, commonsAudioUrl, RU_LABELS,
};
