# -*- coding: utf-8 -*-
"""Shared pieces of the Verbs of Motion course: the Wiktionary data (definitions
and conjugation tables for every verb, tools/courses/motion_src/wiktionary_verbs.json,
CC BY-SA 4.0) drawn as course tables, and the mined sentences (motion_drills.json)."""
import io, json, os, re
from kit import *

HERE = os.path.dirname(os.path.abspath(__file__))
WIKT = json.load(io.open(os.path.join(HERE, "motion_src", "wiktionary_verbs.json"), encoding="utf-8"))
_dp = os.path.join(HERE, "motion_drills.json")
DRILLS = json.load(io.open(_dp, encoding="utf-8")) if os.path.exists(_dp) else {}

WIKT_URL = "https://en.wiktionary.org/wiki/"
WP = "Wikipedia, «Russian grammar» (https://en.wikipedia.org/wiki/Russian_grammar#Verbs_of_motion, CC BY-SA 4.0)"
DLI = "DLI Russian Basic Course, Grammar Reference Book"
SOURCES = NOTE("Lesson text quoted from the Defense Language Institute Russian Basic Course, Grammar Reference Books I (1970) and II (1965), a US Government work in the public domain "
               "(https://www.fsi-language-courses.org/russian/courses/dli-russian-basic-course), from the English Wikipedia's article «Russian grammar», section «Verbs of motion» "
               "(https://en.wikipedia.org/wiki/Russian_grammar#Verbs_of_motion, CC BY-SA 4.0), and from the English Wiktionary's entries for each verb, named where a table is given "
               "(https://en.wiktionary.org/, CC BY-SA 4.0). Exercises: sentences and translations from Tatoeba (https://tatoeba.org/, CC BY 2.0 FR) and sentences from the library's public-domain books; "
               "the answer is always the word the sentence has.")


def entry(lemma, aspect=None):
    """The Wiktionary entry for `lemma` (the one of the given aspect, if the page has two)."""
    ents = WIKT.get(lemma) or []
    if aspect:
        for e in ents:
            if re.search(r"\b" + aspect + r"\b", e.get("head") or ""):
                return e
    for e in ents:
        if e.get("c"):
            return e
    return ents[0] if ents else None


def head(lemma, aspect=None):
    e = entry(lemma, aspect)
    c = e and e.get("c")
    return (c and c.get("inf")) or lemma


def defs(lemma, n=3, aspect=None):
    e = entry(lemma, aspect)
    out = []
    for d in (e and e.get("defs")) or []:
        d = d.strip()
        if d and not re.match(r"^(passive|reflexive|inflection) of", d, re.I):
            out.append(d)
    return "; ".join(out[:n])


def cite(*lemmas):
    """A Wiktionary citation line for the verbs tabled, each page named."""
    return NOTE("; ".join("Wiktionary, «%s» (%s%s, CC BY-SA 4.0)" % (l, WIKT_URL, l) for l in lemmas))


PERSONS = ["я", "ты", "он, она", "мы", "вы", "они"]


def conj_table(lemmas, caption=None, aspects=None):
    """One column per verb: present (or the perfective future), past, imperative — Wiktionary's forms."""
    cols, data = [], []
    for i, l in enumerate(lemmas):
        e = entry(l, aspects[i] if aspects else None)
        c = (e and e.get("c")) or {}
        pres = c.get("pres") or []
        fut = c.get("fut") or []
        simple = pres if any(pres) else fut
        cols.append(c.get("inf") or l)
        past = c.get("past") or {}
        imp = c.get("imp") or []
        data.append({"forms": simple, "past": past, "imp": imp, "pf": not any(pres)})
    rows = []
    for k, who in enumerate(PERSONS):
        rows.append([who] + [(d["forms"][k] if k < len(d["forms"]) else "").replace(", ", " ") for d in data])
    rows.append(["past: он / она / они"] + [" / ".join(x for x in (d["past"].get("m", ""), d["past"].get("f", ""), d["past"].get("pl", "")) if x) for d in data])
    rows.append(["imperative"] + [" / ".join(x for x in d["imp"] if x) for d in data])
    hd = [""] + ["**%s**%s" % (cols[i], " (pf.: future)" if data[i]["pf"] else "") for i in range(len(cols))]
    return T(hd, rows, caption=caption)


def pair_table(pairs, caption=None):
    """Unidirectional / multidirectional, with Wiktionary's gloss and its я- and ты-forms."""
    rows = []
    for uni, multi in pairs:
        cu, cm = (entry(uni) or {}).get("c") or {}, (entry(multi) or {}).get("c") or {}
        fu = [x for x in (cu.get("pres") or [])[:2] if x]
        fm = [x for x in (cm.get("pres") or [])[:2] if x]
        rows.append(["**%s** — %s" % (cu.get("inf", uni), ", ".join(fu)), "**%s** — %s" % (cm.get("inf", multi), ", ".join(fm)),
                     defs(uni, 2)])
    return T(["one direction", "many directions, or there and back", "Wiktionary's definition"], rows, caption=caption, row_heads=False)


def drills(sid):
    d = DRILLS.get(sid) or {}
    return list(d.get("ex") or []), list(d.get("more") or [])


def prefixed_table(prefix_lemmas, caption=None):
    """perfective / imperfective pairs for a prefix, each with Wiktionary's definition."""
    rows = []
    for pf, ipf in prefix_lemmas:
        rows.append(["**%s**" % head(pf, "pf"), "**%s**" % head(ipf, "impf"), defs(pf, 2, "pf") or defs(ipf, 2, "impf")])
    return T(["perfective", "imperfective", "Wiktionary's definition"], rows, caption=caption, row_heads=False)
