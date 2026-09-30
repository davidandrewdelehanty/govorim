#!/usr/bin/env python3
"""Follow the pointer on an untagged 'inflection of X' page.

freedictionaryapi tags most form-of senses ("form of"), but not the ones it
flattens out of Wiktionary's grouped inflection lines — those arrive with no
tags at all. api/define.js only recognised the tag, so «венчания» answered
with "inflection of венчание (venčánije):" and no meaning behind it, while
the lemma's page had "wedding; coronation" all along. This teaches it to read
the sense text too, and to follow a pointer up to two hops.
"""
import sys

p = sys.argv[1]
s = open(p, encoding="utf-8").read()


def rep(old, new, count=1):
    global s
    n = s.count(old)
    assert n == count, (n, old[:70])
    s = s.replace(old, new)


rep(
    'function isFormOf(sense) { return hasTag(sense && sense.tags, "form of"); }',
    '''// A sense that says what FORM the word is — "genitive singular of стол",
// "inflection of венчание:" — rather than what it means. Most arrive tagged
// "form of", but the ones the upstream API flattens out of Wiktionary's
// grouped inflection lines carry no tags at all, and those were being served
// to the reader as though the grammatical note were the definition. So the
// text is read as well as the tag.
//
// Anchored at the start on purpose: a real definition can name a lemma in
// passing — ноша is "load, burden (verbal noun of нести)" — and only a gloss
// that BEGINS with the grammar words is a pointer rather than a meaning.
// Checked against 122 senses of 50 words: agrees with the tag everywhere it
// exists, and adds exactly the untagged "inflection of X:" pages.
const FORM_OF_RE = new RegExp(
  "^\\\\s*(?:\\\\([^)]*\\\\)\\\\s*)?(?:" +
  "inflection|inflected|form|forms|spelling|plural|singular|genitive|dative|" +
  "accusative|instrumental|prepositional|nominative|vocative|locative|partitive|" +
  "comparative|superlative|diminutive|augmentative|participle|gerund|infinitive|" +
  "imperative|indicative|subjunctive|past|present|future|masculine|feminine|" +
  "neuter|animate|inanimate|short|long|reflexive|perfective|imperfective|" +
  "romanization|romanisation|misspelling|abbreviation|contraction|alternative|" +
  "obsolete|archaic|dated|pre-reform|adverbial|passive|active|" +
  "first-person|second-person|third-person" +
  ")\\\\b[^.]{0,60}?\\\\bof\\\\s+[\\\\u0400-\\\\u04ff]", "i");

function isFormOf(sense) {
  if (hasTag(sense && sense.tags, "form of")) return true;
  return FORM_OF_RE.test(String((sense && sense.definition) || ""));
}

// The grammatical relation, tidied for display: no romanisation in brackets,
// no dangling colon from a grouped "inflection of X:" line.
function cleanFormNote(text) {
  return String(text || "")
    .replace(/\\s*\\([^)]*\\)/g, "")
    .replace(/[\\s:;,.]+$/, "")
    .replace(/\\s+/g, " ")
    .trim()
    .slice(0, 80);
}''',
)

# The note, on the entry built from the LEMMA's page: drop the pointer when it
# repeats the headword the popup is already showing.
rep(
    '  if (formNote) bits.push(formNote);',
    '''  if (formNote) {
    // "genitive singular of венчание" beside a headword that already reads
    // венчание is the same word twice: keep the grammar, drop the pointer.
    let fn = formNote.replace(/\\s+of\\s+([\\u0400-\\u04ff\\u0300-\\u036f-]+)(\\s+(?:impf|pf)\\.?)?\\s*$/i,
      function (m, w) { return deaccent(w).toLowerCase() === lemma.toLowerCase() ? "" : m; }).trim();
    if (/^inflection$/i.test(fn)) fn = "inflected form";
    bits.push(fn || formNote);
  }''',
)

rep(
    '''    const note = String((realSenses(direct)[0] || {}).definition || "").slice(0, 80);
    // The structured pointer is missing on plenty of Russian form-of pages, so
    // the lemma is read out of the sense text as well — "genitive singular of
    // фраер" names the word it wants us to look at.
    const ptr = lemmaPointer(direct || {}) || lemmaFromNote(note);
    if (ptr && ptr !== cand) {
      const lemPack = await wiktFetch(ptr, signal);
      if (lemPack) {
        const built = buildWiktEntry(lemPack, clickedWord, cand, note);
        if (built) return finish(built);
      }
    }''',
    '''    const note = cleanFormNote((realSenses(direct)[0] || {}).definition);
    // The structured pointer is missing on plenty of Russian form-of pages, so
    // the lemma is read out of the sense text as well — "genitive singular of
    // фраер" names the word it wants us to look at.
    let ptr = lemmaPointer(direct || {}) || lemmaFromNote(note);
    // Up to two hops: a form can point at another form (a participle at its
    // verb, a comparative at an adjective that is itself a short form). The
    // note stays the FIRST one — it describes the word actually clicked.
    const seen = {};
    seen[String(cand).toLowerCase()] = true;
    for (let hop = 0; hop < 2 && ptr && !seen[ptr.toLowerCase()]; hop++) {
      if (timeLeft && timeLeft() < 900) break;
      seen[ptr.toLowerCase()] = true;
      const lemPack = await wiktFetch(ptr, signal);
      if (!lemPack) break;
      for (const r of readingsFromWikt(lemPack, ptr)) addReading(readings, r.lemma, r.pos, r.note);
      const lemEntry = pickEntry(lemPack.entries);
      if (definedSenses(lemEntry).some(function (s) { return !isFormOf(s); })) {
        const built = buildWiktEntry(lemPack, clickedWord, cand, note);
        if (built) return finish(built);
        break;
      }
      ptr = lemmaPointer(lemEntry || {}) || lemmaFromNote((realSenses(lemEntry)[0] || {}).definition);
    }''',
)

open(p, "w", encoding="utf-8", newline="\n").write(s)
print("ok")
