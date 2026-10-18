// ---- English words, defined in Russian, from Русский Викисловарь -------------
// The English column of a parallel book is clickable: a tapped English word
// opens its entry in ru.wiktionary, which describes English words in Russian
// («anger» — гнев, злоба, ярость). That is the point of the feature: a reader
// who meets an English word in the translation gets the Russian for it, from
// a dictionary, and from the same dictionary the Russian side already trusts.
//
// English words are inflected (walked, cities, went), and ru.wiktionary has
// pages for few of the forms, so the tapped word is turned into a short list
// of likely headwords — itself, an irregular-form lookup, then suffix
// stripping — and all of them are asked for in ONE API request. The first
// that has an English section with at least one sense wins. Nothing is
// guessed beyond that: no entry means "not in the dictionary".

import { scanTemplates, templateArgs, cleanWiki, sectionBody } from "./ruwikt.js";

const API = "https://ru.wiktionary.org/w/api.php";
const UA = "SamovarReader/1.0 (https://samovar.live; dictionary lookup for a Russian reading site)";

const IRREGULAR = {
  am: "be", is: "be", are: "be", was: "be", were: "be", been: "be", being: "be",
  has: "have", had: "have", having: "have", does: "do", did: "do", done: "do",
  went: "go", gone: "go", goes: "go", said: "say", says: "say", saw: "see", seen: "see",
  came: "come", took: "take", taken: "take", made: "make", knew: "know", known: "know",
  thought: "think", told: "tell", found: "find", gave: "give", given: "give", left: "leave",
  felt: "feel", brought: "bring", began: "begin", begun: "begin", kept: "keep", held: "hold",
  stood: "stand", heard: "hear", ran: "run", sat: "sit", spoke: "speak", spoken: "speak",
  wrote: "write", written: "write", got: "get", gotten: "get", met: "meet", led: "lead",
  lay: "lie", lain: "lie", laid: "lay", sent: "send", spent: "spend", built: "build",
  fell: "fall", fallen: "fall", rose: "rise", risen: "rise", drew: "draw", drawn: "draw",
  grew: "grow", grown: "grow", threw: "throw", thrown: "throw", flew: "fly", flown: "fly",
  ate: "eat", eaten: "eat", drank: "drink", drunk: "drink", sang: "sing", sung: "sing",
  swam: "swim", rode: "ride", ridden: "ride", wore: "wear", worn: "wear", tore: "tear",
  torn: "tear", broke: "break", broken: "break", chose: "choose", chosen: "choose",
  forgot: "forget", forgotten: "forget", froze: "freeze", frozen: "freeze", hid: "hide",
  hidden: "hide", shook: "shake", shaken: "shake", stole: "steal", stolen: "steal",
  struck: "strike", fought: "fight", caught: "catch", taught: "teach", bought: "buy",
  sought: "seek", slept: "sleep", wept: "weep", swept: "sweep", lost: "lose", paid: "pay",
  heard: "hear", understood: "understand", became: "become", woke: "wake", woken: "wake",
  bore: "bear", borne: "bear", born: "bear", sold: "sell", won: "win", hung: "hang",
  shone: "shine", shot: "shoot", fed: "feed", fled: "flee", bled: "bleed", bent: "bend",
  lent: "lend", meant: "mean", dealt: "deal", dreamt: "dream", knelt: "kneel", leapt: "leap",
  slid: "slide", spun: "spin", stuck: "stick", stung: "sting", swore: "swear", sworn: "swear",
  wound: "wind", dug: "dig", clung: "cling", sprang: "spring", sprung: "spring",
  men: "man", women: "woman", children: "child", feet: "foot", teeth: "tooth",
  geese: "goose", mice: "mouse", oxen: "ox", lives: "life", wives: "wife", knives: "knife",
  wolves: "wolf", leaves: "leaf", halves: "half", selves: "self", thieves: "thief",
  better: "good", best: "good", worse: "bad", worst: "bad", further: "far", farther: "far",
  me: "I", him: "he", her: "she", us: "we", them: "they", thee: "thou", thy: "thou",
  hath: "have", doth: "do", art: "be", wast: "be", wert: "be", hast: "have", didst: "do",
};

export function englishCandidates(raw) {
  const w0 = String(raw || "").replace(/[’]/g, "'").replace(/'s$/i, "").replace(/[^A-Za-z'-]/g, "");
  const w = w0.toLowerCase();
  const out = [];
  const add = function (x) { if (x && x.length > 1 && out.indexOf(x) === -1) out.push(x); };
  if (!w) return out;
  add(w);
  if (w0 !== w) add(w0);                       // a name: Achilles, Hector
  if (IRREGULAR[w]) add(IRREGULAR[w]);
  const dbl = function (s) { return /([bcdfgklmnprstvz])\1$/.test(s) ? s.slice(0, -1) : null; };
  let m;
  if ((m = /^(.+)ies$/.exec(w))) add(m[1] + "y");
  if ((m = /^(.+?)(ses|xes|zes|ches|shes|oes)$/.exec(w))) add(m[1] + m[2].slice(0, -2));
  if ((m = /^(.+[^s])s$/.exec(w))) add(m[1]);
  if ((m = /^(.+)ied$/.exec(w))) add(m[1] + "y");
  if ((m = /^(.+)ed$/.exec(w))) { add(m[1]); add(m[1] + "e"); add(dbl(m[1])); }
  if ((m = /^(.+)ing$/.exec(w))) { add(m[1]); add(m[1] + "e"); add(dbl(m[1])); }
  if ((m = /^(.+)ier$/.exec(w))) add(m[1] + "y");
  if ((m = /^(.+)iest$/.exec(w))) add(m[1] + "y");
  if ((m = /^(.+)er$/.exec(w))) { add(m[1]); add(m[1] + "e"); add(dbl(m[1])); }
  if ((m = /^(.+)est$/.exec(w))) { add(m[1]); add(m[1] + "e"); add(dbl(m[1])); }
  if ((m = /^(.+)ly$/.exec(w))) { add(m[1]); if (/i$/.test(m[1])) add(m[1].slice(0, -1) + "y"); }
  return out.slice(0, 12);
}

function englishSection(text) {
  const m = /(^|\n)=\s*\{\{\s*(?:-en-|язык\|en)\s*\}\}\s*=/i.exec(text);
  if (!m) return "";
  const rest = text.slice(m.index + m[0].length);
  const next = /\n=\s*\{\{[^}]*\}\}\s*=(?!=)/.exec(rest);
  return next ? rest.slice(0, next.index) : rest;
}

const POS = [
  [/\{\{\s*сущ\s+en/i, "сущ."], [/\{\{\s*гл\s+en/i, "гл."], [/\{\{\s*прил\s+en/i, "прил."],
  [/\{\{\s*нареч\s+en/i, "нареч."], [/\{\{\s*мест\s+en/i, "мест."], [/\{\{\s*предл\s+en/i, "предлог"],
  [/\{\{\s*союз\s+en/i, "союз"], [/\{\{\s*числ\s+en/i, "числ."], [/\{\{\s*межд\s+en/i, "межд."],
  [/\{\{\s*part\s+en|\{\{\s*частица\s+en/i, "частица"], [/\{\{\s*article\s+en|\{\{\s*артикль/i, "артикль"],
];

// {{значение|определение=…|пометы=…}} written over several lines.
function unfold(body) {
  if (String(body || "").indexOf("{{значение") < 0) return body;
  return scanTemplates(body, function (inner) {
    const args = templateArgs(inner);
    if (args[0].trim().toLowerCase() !== "значение") return "{{" + inner + "}}";
    let def = "", marks = "";
    for (const a of args.slice(1)) {
      const mm = /^\s*([а-яё]+)\s*=\s*([\s\S]*)$/i.exec(a);
      if (!mm) continue;
      if (mm[1] === "определение") def = mm[2];
      else if (mm[1] === "пометы") marks = mm[2];
    }
    return (marks.trim() + " " + def.trim()).replace(/\s*\n\s*/g, " ").trim();
  });
}

function ipaOf(sec) {
  const m = /\{\{\s*transcriptions?\s*\|([^|}]*)/i.exec(sec);
  const v = m && m[1].trim();
  return v ? v.split(",")[0].trim() : "";
}

export function parseEnglishEntry(text) {
  const sec = englishSection(text || "");
  if (!sec) return null;
  // Homonyms and parts of speech each sit under their own "== … ==" block.
  const blocks = sec.split(/\n==\s*\{\{\s*заголовок[^\n]*==\s*\n/);
  const entries = [];
  for (const b of blocks) {
    let pos = "";
    for (const [re, label] of POS) { if (re.test(b)) { pos = label; break; } }
    const body = unfold(sectionBody("\n" + b, "Значение"));
    const senses = [];
    for (const line of String(body).split("\n")) {
      if (!/^#(?![:*])/.test(line)) continue;
      const t = cleanWiki(line.replace(/^#+\s*/, ""));
      if (t && t !== "-" && senses.indexOf(t) === -1) senses.push(t);
      if (senses.length >= 6) break;
    }
    if (senses.length) entries.push({ pos: pos, senses: senses });
  }
  if (!entries.length) return null;
  return { ipa: ipaOf(sec), entries: entries };
}

export async function englishLookup(raw, signal) {
  const cands = englishCandidates(raw);
  if (!cands.length) return null;
  const url = API + "?action=query&prop=revisions&rvprop=content&rvslots=main&format=json&formatversion=2" +
    "&redirects=1&origin=*&titles=" + encodeURIComponent(cands.join("|"));
  let resp = await fetch(url, { signal, headers: { accept: "application/json", "user-agent": UA, "api-user-agent": UA } });
  if (resp.status === 429) {
    await new Promise(function (r) { setTimeout(r, 800); });
    resp = await fetch(url, { signal, headers: { accept: "application/json", "user-agent": UA, "api-user-agent": UA } });
  }
  if (!resp.ok) { const e = new Error("ru.wiktionary returned HTTP " + resp.status); e.status = resp.status; throw e; }
  const data = await resp.json();
  const q = (data && data.query) || {};
  // Map each asked title through normalisation and redirects to the page it landed on.
  const hop = {};
  for (const n of (q.normalized || [])) hop[n.from] = n.to;
  for (const r of (q.redirects || [])) hop[r.from] = r.to;
  const byTitle = {};
  for (const p of (q.pages || [])) {
    if (p.missing || !p.revisions) continue;
    byTitle[p.title] = p.revisions[0].slots.main.content;
  }
  for (const c of cands) {
    let t = c, guard = 0;
    while (hop[t] && guard++ < 3) t = hop[t];
    const text = byTitle[t];
    if (!text) continue;
    const parsed = parseEnglishEntry(text);
    if (!parsed) continue;
    return {
      word: String(raw), lemma: t, ipa: parsed.ipa, entries: parsed.entries,
      source: "ru.wiktionary", sourceUrl: "https://ru.wiktionary.org/wiki/" + encodeURIComponent(t.replace(/ /g, "_")),
    };
  }
  return null;
}
