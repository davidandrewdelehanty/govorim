// lib/bible.js — the Bible's own dictionary, for the Synodal Bible alone.
//
// The words no dictionary has are, in the Bible, mostly the Bible's own:
// ефод, виссон, мытарь, синедрион, the names of people and places. Archimandrite
// Nikifor's «Иллюстрированная полная популярная библейская энциклопедия»
// (Moscow, 1891–92; about 7,500 entries, each keyed to the Russian Bible) is
// in the public domain and transcribed on the Russian Wikisource under
// БЭАН/<headword>. This asks it for a word — only when the reader is in the
// Synodal Bible (the client says so), and only after every dictionary has
// declined the word (api/define.js runs it last), so a Bible sense never
// shadows an ordinary one: «язык» in the Bible is still a tongue first.
//
// Two requests: the headwords that begin with the word (one call for each
// candidate form, in parallel), then the article text of the headwords that
// match. The article's opening is returned, cut at a sentence; the rest is a
// tap away on Wikisource.

const WS_API = "https://ru.wikisource.org/w/api.php";
const PREFIX = "БЭАН/";
const WS_URL = "https://ru.wikisource.org/wiki/";
const LEAD_MAX = 700;
export const BIBLE_SOURCE = "Библейская энциклопедия архимандрита Никифора (1891)";

const UA = "SamovarReader/1.0 (https://samovar.live; dictionary lookup for a Russian reading site)";
const memo = new Map();
const MEMO_MAX = 400;
async function wsFetch(url, signal) {
  const hit = memo.get(url);
  if (hit) return hit;
  const go = function () {
    return fetch(url, { signal, headers: { accept: "application/json", "user-agent": UA, "api-user-agent": UA } });
  };
  let resp = await go();
  if (resp.status === 429 || resp.status >= 500) {
    let wait = 700;
    const ra = parseFloat(resp.headers && resp.headers.get && resp.headers.get("retry-after"));
    if (ra > 0) wait = Math.min(1500, ra * 1000);
    await new Promise(function (r) { setTimeout(r, wait); });
    resp = await go();
  }
  if (!resp.ok) return null;
  const data = await resp.json();
  if (memo.size >= MEMO_MAX) memo.delete(memo.keys().next().value);
  memo.set(url, data);
  return data;
}

function capFirst(w) {
  w = String(w || "");
  return w ? w.charAt(0).toUpperCase() + w.slice(1) : w;
}
function fold(w) {
  return String(w || "").toLowerCase().replace(/ё/g, "е").replace(/́/g, "").trim();
}

// The headwords a title names: «Аварим, Аваримские горы» names two, «Авва
// (город)» names one with a gloss that is not part of the word.
function headsOf(title) {
  const t = String(title || "").slice(PREFIX.length).replace(/\s*\([^)]*\)\s*$/, "");
  return t.split(/\s*,\s*/).map(fold).filter(Boolean);
}

// The encyclopedia's titles for a word: those beginning with it, kept when
// one of the headwords they name IS the word. Several forms are asked in
// parallel (the form on the page, its ё-less spelling, the lemmas), and the
// first form with a title wins — the page's own spelling before a guess.
export async function bibleTitles(cands, signal) {
  const forms = (cands || []).map(fold).filter(function (w, i, a) { return w && a.indexOf(w) === i; }).slice(0, 5);
  if (!forms.length) return [];
  const lists = await Promise.all(forms.map(async function (f) {
    // A letter short of the form, so that a plural headword is in the list.
    const pre = f.length >= 5 ? f.slice(0, -1) : f;
    const url = WS_API + "?action=query&format=json&formatversion=2&list=allpages&aplimit=40" +
      "&apprefix=" + encodeURIComponent(PREFIX + capFirst(pre));
    const data = await wsFetch(url, signal);
    const pages = (data && data.query && data.query.allpages) || [];
    return pages.map(function (p) { return p.title; });
  }));
  for (let i = 0; i < lists.length; i++) {
    const exact = lists[i].filter(function (t) { return headsOf(t).indexOf(forms[i]) >= 0; });
    if (exact.length) return { form: forms[i], titles: exact.slice(0, 3) };
  }
  // The encyclopedia heads a people or a class in the plural — Фарисеи,
  // Левиты, Саддукеи — where the lemma is singular. The plural of the form
  // counts, and nothing looser: a near miss would be the wrong article.
  for (let i = 0; i < lists.length; i++) {
    const f = forms[i];
    if (f.length < 4) continue;
    const plurals = [f + "ы", f + "и", f.slice(0, -1) + "и", f.slice(0, -1) + "ы", f.slice(0, -1) + "а", f.slice(0, -1) + "я"];
    const near = lists[i].filter(function (t) {
      return headsOf(t).some(function (h) { return plurals.indexOf(h) >= 0; });
    });
    if (near.length) return { form: forms[i], titles: near.slice(0, 3) };
  }
  // Last, a headword of several words that opens with the form: «Ковчег
  // Завета» for ковчег, «Хлебы предложения» for хлебы. The popup shows the
  // whole headword, so the reader sees what was found.
  for (let i = 0; i < lists.length; i++) {
    const f = forms[i];
    if (f.length < 4) continue;
    const opens = lists[i].filter(function (t) {
      return headsOf(t).some(function (h) { return h.indexOf(f + " ") === 0; });
    });
    if (opens.length) return { form: forms[i], titles: opens.slice(0, 3) };
  }
  return null;
}

// Wikitext to prose: the header template off, the Bible references as the
// text the transcribers display («Исх. XXVIII, 1»), links and emphasis to
// their words, tags and categories gone.
export function cleanWikitext(t) {
  let s = String(t || "");
  s = s.replace(/^\s*\{\{БЭАН[\s\S]*?\}\}\s*/, "");
  s = s.replace(/<!--[\s\S]*?-->/g, "");
  s = s.replace(/<ref[^>]*\/>/gi, "").replace(/<ref[^>]*>[\s\S]*?<\/ref>/gi, "");
  s = s.replace(/\{\{Библия\|([^{}]*)\}\}/g, function (m, inner) {
    const parts = inner.split("|");
    const shown = parts.filter(function (p) { return /^\s*т\s*=/.test(p); })[0];
    if (shown) return shown.replace(/^\s*т\s*=/, "").trim();
    return (parts[1] || "").trim();
  });
  for (let i = 0; i < 3; i++) s = s.replace(/\{\{[^{}]*\}\}/g, " ");
  s = s.replace(/\[\[(?:Категория|Category):[^\]]*\]\]/gi, "");
  s = s.replace(/\[\[(?:[^\]|]*\|)?([^\]]*)\]\]/g, "$1");
  s = s.replace(/\[https?:[^\s\]]*\s*([^\]]*)\]/g, "$1");
  s = s.replace(/'''|''/g, "");
  s = s.replace(/<br\s*\/?>/gi, " ").replace(/<[^>]+>/g, "");
  s = s.replace(/&nbsp;/g, " ").replace(/&[a-z]+;/g, " ");
  s = s.replace(/^=+.*=+\s*$/gm, "");
  s = s.replace(/\(\s*\)/g, "").replace(/,\s*,/g, ",").replace(/\(\s*,/g, "(");
  s = s.replace(/[ \t]+/g, " ").replace(/ *\n */g, "\n").replace(/\n{2,}/g, "\n").trim();
  return s;
}

// The article's opening, whole sentences, within the popup's room.
export function leadOf(prose, max) {
  max = max || LEAD_MAX;
  const paras = String(prose || "").split("\n").map(function (p) { return p.trim(); }).filter(Boolean);
  let out = paras.join("\n");
  if (out.length > max) {
    const cut = out.slice(0, max);
    const k = Math.max(cut.lastIndexOf(". "), cut.lastIndexOf(".\n"), cut.lastIndexOf("; "), cut.lastIndexOf(") "));
    out = (k > max * 0.5 ? cut.slice(0, k + 1) : cut).trim() + " …";
  }
  return out;
}

export async function bibleLookup(cands, clickedWord, signal) {
  const found = await bibleTitles(cands, signal);
  if (!found) return null;
  const url = WS_API + "?action=query&format=json&formatversion=2&prop=revisions&rvprop=content&rvslots=main" +
    "&titles=" + encodeURIComponent(found.titles.join("|"));
  const data = await wsFetch(url, signal);
  const pages = (data && data.query && data.query.pages) || [];
  const senses = [];
  const titles = [];
  for (const t of found.titles) {
    const pg = pages.filter(function (p) { return p && p.title === t && !p.missing; })[0];
    const raw = pg && pg.revisions && pg.revisions[0] && pg.revisions[0].slots && pg.revisions[0].slots.main && pg.revisions[0].slots.main.content;
    const lead = leadOf(cleanWikitext(raw));
    if (lead.length < 12) continue;
    senses.push(lead);
    titles.push(t);
  }
  if (!senses.length) return null;
  const head = titles[0].slice(PREFIX.length).replace(/\s*\([^)]*\)\s*$/, "").split(/\s*,\s*/)[0];
  return {
    word: clickedWord,
    lemma: head,
    matchedForm: found.form,
    partOfSpeech: "",
    aspect: "",
    aspectPair: "",
    translation: senses[0],
    ruSenses: senses.length > 1 ? senses : undefined,
    noEnglish: true,
    definitionSource: "bible",
    grammar: "",
    sourceUrl: WS_URL + encodeURIComponent(titles[0]).replace(/%2F/g, "/"),
    sourceNote: BIBLE_SOURCE,
    bibleTitles: titles.map(function (t) { return t.slice(PREFIX.length); }),
  };
}
