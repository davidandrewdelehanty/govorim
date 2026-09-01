// Russian lemma guessing, by rule.
//
// The dictionary tiers are keyed by page title, so an inflected click has to be
// turned back into a headword before any of them can answer. On govorim.dev
// Yandex does that server-side with its MORPHO flag; Samovar has no Yandex, so
// the surface form has to be rewritten here.
//
// This is deliberately a GUESS GENERATOR rather than a morphological analyser.
// Guessing is safe because nothing is trusted: every candidate is checked
// against real dictionary pages before it is used, and a wrong guess simply
// isn't a word anybody has written an entry for. That trade buys full coverage
// of regular Russian inflection — which is most of it — for one small table and
// no data files.
//
// Rules are tried longest-suffix-first, so "кипежну-лся" is read as a
// reflexive past before the bare "-л" rule ever sees it.

const RULES = [
  // ---- verbs: reflexive past and present ----------------------------------
  ["вшись", ["ться"]],
  ["лась", ["ться"]], ["лось", ["ться"]], ["лись", ["ться"]],
  ["ется", ["ться", "аться"]], ["ются", ["ться", "аться"]],
  ["ится", ["иться"]], ["ятся", ["иться", "яться"]],
  ["лся", ["ться"]],
  // ---- verbs: participles --------------------------------------------------
  ["вший", ["ть"]], ["вшая", ["ть"]], ["вшие", ["ть"]],
  ["нный", ["ть"]], ["тый", ["ть"]],
  // ---- verbs: past ---------------------------------------------------------
  // A handful of irregular pasts that no ending rule reaches: подошёл → подойти,
  // разжёг → разжечь.
  ["шёл", ["йти", "ти"]], ["шел", ["йти", "ти"]], ["шла", ["йти"]], ["шли", ["йти"]],
  ["ёг", ["ечь"]], ["ег", ["ечь"]], ["ёк", ["ечь"]],
  ["ал", ["ать"]], ["ял", ["ять"]], ["ел", ["еть", "ть"]],
  ["ил", ["ить"]], ["ул", ["уть"]], ["ыл", ["ыть"]], ["ол", ["оть"]],
  ["ла", ["ть"]], ["ло", ["ть"]], ["ли", ["ть"]], ["л", ["ть"]],
  // ---- verbs: present ------------------------------------------------------
  ["ешь", ["ать", "ть"]], ["ёшь", ["ать", "ть"]], ["ишь", ["ить"]],
  ["ете", ["ать"]], ["ите", ["ить"]],
  ["ают", ["ать"]], ["яют", ["ять"]], ["уют", ["овать"]], ["юют", ["евать"]],
  ["ют", ["ать", "ть"]], ["ут", ["ать", "ть"]],
  ["ят", ["ить", "ять"]], ["ат", ["ать"]],
  ["ает", ["ать"]], ["ёт", ["ать", "ть"]], ["ет", ["ать", "ть"]], ["ит", ["ить"]],
  // ---- adjectives ----------------------------------------------------------
  ["ого", ["ый", "ий", "ой"]], ["его", ["ий", "ый"]],
  ["ому", ["ый", "ий"]], ["ему", ["ий", "ый"]],
  ["ыми", ["ый"]], ["ими", ["ий", "ый"]],
  ["ых", ["ый", "ой"]], ["их", ["ий", "ый", "ой"]],
  ["ые", ["ый", "ой"]], ["ие", ["ий", "ый", "ой"]],
  ["ую", ["ая", "ый"]], ["юю", ["яя", "ий"]],
  ["ая", ["ый"]], ["яя", ["ий"]],
  ["ое", ["ый"]], ["ее", ["ий"]],
  // ---- nouns ---------------------------------------------------------------
  ["ами", ["а", "я", ""]], ["ями", ["я", "ь", ""]],
  ["ах", ["а", "я", ""]], ["ях", ["я", "ь", ""]],
  ["ов", [""]], ["ев", ["ь", ""]], ["ёв", ["ь", ""]],
  ["ам", ["а", "я", ""]], ["ям", ["я", "ь", ""]],
  ["ою", ["а"]], ["ой", ["а", "ый"]], ["ей", ["я", "ь", "ий"]],
  ["ом", [""]], ["ем", ["ь", "", "ать"]], ["им", ["ий", "ый", "ить"]],
  ["ы", ["а", ""]], ["и", ["а", "я", "ь", ""]],
  ["у", ["", "а"]], ["ю", ["ь", "я", "ать", "ить", "еть", "ть"]],
  ["е", ["а", "я", "о", "ь", ""]],
  ["а", ["", "а"]], ["я", ["ь", "я", ""]],
  ["о", ["о", ""]],
];

function foldRu(s) { return String(s || "").toLowerCase().replace(/ё/g, "е"); }

// The same test the search-based resolver uses: only the ENDINGS may differ,
// and endings are short. «кент» and «кентавр» share four letters and are
// unrelated words.
function endingsOnly(surface, candidate) {
  const a = foldRu(surface), b = foldRu(candidate);
  if (!a || !b || b === a) return false;
  if (b.length < 3) return false;
  let common = 0;
  while (common < a.length && common < b.length && a[common] === b[common]) common++;
  if (common < Math.max(3, Math.ceil(0.5 * Math.min(a.length, b.length)))) return false;
  if (b.length - common > 4) return false;
  if (a.length - common > 4) return false;
  return true;
}

// First-person present forms mutate the stem's last consonant, which no
// ending rule can undo: ношу is носить, вижу is видеть, люблю is любить.
// These are the regular alternations of Russian conjugation, tried only on a
// form ending in -у/-ю, and only as guesses — the page check decides.
const MUTATIONS = [
  ["ш", ["с"]], ["ж", ["д", "з", "г"]], ["ч", ["т", "к"]], ["щ", ["ст", "ск", "т"]],
  ["бл", ["б"]], ["вл", ["в"]], ["пл", ["п"]], ["мл", ["м"]], ["фл", ["ф"]],
];
function mutatedInfinitives(w) {
  const m = /^(.+?)(у|ю)$/.exec(w);
  if (!m) return [];
  const stem = m[1], out = [];
  for (const rule of MUTATIONS) {
    const mut = rule[0];
    if (stem.length <= mut.length || stem.slice(-mut.length) !== mut) continue;
    const base = stem.slice(0, stem.length - mut.length);
    for (const orig of rule[1]) for (const inf of ["ить", "еть", "ать"]) out.push(base + orig + inf);
  }
  return out;
}

// Ordered guesses at the headword behind an inflected form. Most likely first;
// the caller checks which of them are real pages.
export function lemmaCandidates(word, max) {
  const w = String(word || "").toLowerCase().trim();
  const out = [];
  const seen = Object.create(null);
  seen[foldRu(w)] = true;                       // the surface form is not a guess
  const limit = max || 12;
  for (const cand of mutatedInfinitives(w)) {
    const key = foldRu(cand);
    if (seen[key]) continue;
    seen[key] = true;
    out.push(cand);
    if (out.length >= limit) return out;
  }
  for (const rule of RULES) {
    const suffix = rule[0];
    if (w.length <= suffix.length + 1) continue;
    if (w.slice(-suffix.length) !== suffix) continue;
    const stem = w.slice(0, w.length - suffix.length);
    for (const add of rule[1]) {
      const cand = stem + add;
      const key = foldRu(cand);
      if (seen[key]) continue;
      if (!endingsOnly(w, cand)) continue;
      seen[key] = true;
      out.push(cand);
      if (out.length >= limit) return out;
    }
  }
  return out;
}

export { endingsOnly };
